"""
Brewblox service for Tilt hydrometer
"""
import asyncio
import csv
import os.path
import numpy as np
from pint import UnitRegistry
from bluepy.btle import Scanner, DefaultDelegate
from aiohttp import web
from time import sleep
from concurrent.futures import CancelledError
from brewblox_service import (brewblox_logger,
                              events,
                              features,
                              scheduler)

LOGGER = brewblox_logger("brewblox_tilt")
HISTORY_EXCHANGE = 'brewcast'
ureg = UnitRegistry()
Q_ = ureg.Quantity

IDS = {
    "a495bb10c5b14b44b5121370f02d74de": "Red",
    "a495bb20c5b14b44b5121370f02d74de": "Green",
    "a495bb30c5b14b44b5121370f02d74de": "Black",
    "a495bb40c5b14b44b5121370f02d74de": "Purple",
    "a495bb50c5b14b44b5121370f02d74de": "Orange",
    "a495bb60c5b14b44b5121370f02d74de": "Blue",
    "a495bb70c5b14b44b5121370f02d74de": "Yellow",
    "a495bb80c5b14b44b5121370f02d74de": "Pink"
    }

SG_CAL_FILE_PATH = '/share/SGCal.csv'
TEMP_CAL_FILE_PATH = '/share/tempCal.csv'


def setup(app):
    features.add(app, TiltScanner(app))


class Calibrator():
    def __init__(self, file):
        self.calTables = {}
        self.calPolys = {}
        self.loadFile(file)

    def loadFile(self, file):
        if not os.path.exists(file):
            LOGGER.warning("Calibration file not found: {} . Calibrated "
                           "values won't be provided.".format(file))
            return

        # Load calibration CSV
        with open(file, 'r', newline='') as f:
            reader = csv.reader(f, delimiter=',')
            for line in reader:
                colour = None
                uncal = None
                cal = None

                try:
                    uncal = float(line[1].strip())
                except ValueError:
                    LOGGER.warning(
                        "Uncal value not a float '{}'. Ignoring line.".format(
                            line[1]))
                    continue

                try:
                    cal = float(line[2].strip())
                except ValueError:
                    LOGGER.warning(
                        "Cal value not a float '{}'. Ignoring line.".format(
                            line[2]))
                    continue

                colour = line[0].strip().capitalize()
                if colour not in IDS.values():
                    LOGGER.warning(
                        "Unknown tilt colour '{}'. Ignoring line.".format(
                            line[0]))
                    continue

                if colour not in self.calTables:
                    self.calTables[colour] = {
                        "uncal": [],
                        "cal": []
                    }

                self.calTables[colour]["uncal"].append(uncal)
                self.calTables[colour]["cal"].append(cal)

        # Use polyfit to fit a cubic polynomial curve to calibration values
        # Then create a polynomical from the values produced by polyfit
        for colour in self.calTables:
            x = np.array(self.calTables[colour]["uncal"])
            y = np.array(self.calTables[colour]["cal"])
            z = np.polyfit(x, y, 3)
            self.calPolys[colour] = np.poly1d(z)

        LOGGER.info("Calibration file {} loaded for colours: {}".format(
            file,
            ", ".join(self.calPolys.keys())))

    def calValue(self, colour, value, roundPlaces=0):
        # Use polynomials calculated above to calibrate values
        if colour in self.calPolys:
            return round(self.calPolys[colour](value), roundPlaces)
        else:
            return None


class ScanDelegate(DefaultDelegate):
    def __init__(self, app, loop):
        self.app = app
        self.loop = loop
        self.tiltsFound = set()
        self.noDevicesFound = True
        self.message = {}

        self.sgCal = Calibrator(SG_CAL_FILE_PATH)
        self.tempCal = Calibrator(TEMP_CAL_FILE_PATH)

        DefaultDelegate.__init__(self)

    def getMessage(self):
        return self.message

    def clearMessage(self):
        self.message = {}

    def popMessage(self):
        message = self.getMessage()
        self.clearMessage()
        return message

    def decodeData(self, data):
        # Tilt uses a similar data layout to iBeacons accross manufacturer data
        # hex digits 8 - 50. Digits 8-40 contain the ID of the "colour" of the
        # device. Digits 40-44 contain the temperature in f as an integer.
        # Digits 44-48 contain the specific gravity * 1000 (i.e. the "points)
        # as an integer.
        uuid = data[8:40]
        colour = IDS.get(uuid, None)

        if colour is None:
            # UUID is not for a Tilt
            return None

        temp_f = int(data[40:44], 16)

        raw_sg = int(data[44:48], 16)
        sg = raw_sg/1000

        return {
            "colour": colour,
            "temp_f": temp_f,
            "sg": sg
        }

    def publishData(self,
                    colour,
                    temp_f,
                    cal_temp_f,
                    temp_c,
                    cal_temp_c,
                    sg,
                    cal_sg,
                    rssi):
        self.message[colour] = {
            'Temperature[degF]': temp_f,
            'Temperature[degC]': temp_c,
            'Specific gravity': sg,
            'Signal strength[dBm]': rssi
            }

        if cal_temp_f is not None:
            self.message[colour]['Calibrated temperature[degF]'] = cal_temp_f
        if cal_temp_c is not None:
            self.message[colour]['Calibrated temperature[degC]'] = cal_temp_c
        if cal_sg is not None:
            self.message[colour]['Calibrated specific gravity'] = cal_sg

        LOGGER.debug(self.message[colour])

    def handleData(self, data, rssi):
        decodedData = self.decodeData(data)
        if decodedData is None:
            return

        if decodedData["colour"] not in self.tiltsFound:
            self.tiltsFound.add(decodedData["colour"])
            LOGGER.info("Found Tilt: {}".format(decodedData["colour"]))

        temp_c = Q_(decodedData["temp_f"], ureg.degF).to('degC').magnitude

        cal_temp_f = self.tempCal.calValue(
            decodedData["colour"], decodedData["temp_f"])
        cal_temp_c = None
        if cal_temp_f is not None:
            cal_temp_c = Q_(cal_temp_f, ureg.degF).to('degC').magnitude

        cal_sg = self.sgCal.calValue(
            decodedData["colour"], decodedData["sg"], 3)

        self.publishData(
            decodedData["colour"],
            decodedData["temp_f"],
            cal_temp_f,
            temp_c,
            cal_temp_c,
            decodedData["sg"],
            cal_sg,
            rssi)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        data = {}

        if self.noDevicesFound:
            self.noDevicesFound = False
            LOGGER.info("Loop running & device found (may not be a Tilt)")

        for (adtype, desc, value) in dev.getScanData():
            data[desc] = value

        # Data we want is in Manufacturer
        if "Manufacturer" in data:
            self.handleData(data["Manufacturer"], dev.rssi)


class TiltScanner(features.ServiceFeature):
    def __init__(self, app: web.Application):
        super().__init__(app)
        self._task: asyncio.Task = None
        self.scanner = None
        self.scanDelegate = None

    async def startup(self, app: web.Application):
        self._task = await scheduler.create_task(app, self._run())

    # Cleanup before the service shuts down
    async def shutdown(self, app: web.Application):
        await scheduler.cancel_task(self.app, self._task)
        self._task = None

    def _blockingScanner(self):
        try:
            # In theory, this could just be a single start() & multiple
            # process() Unfortunately, that seems less reliable at
            # returning data. The Tilt updates every 5s so we just run a
            # 11sec scan repeatedly. This seems pretty reliable
            self.scanner.scan(timeout=11)

        # This exception is raised when the task is cancelled
        # (scheduler.cancel_task()). It means we're gracefully shutting
        # down. No need to complain or log errors.
        except CancelledError:
            return

        # All other errors are still errors - something bad happened
        # Wait a second, and then continue running
        except Exception as ex:
            LOGGER.error(f'Encountered an error: {ex}')
            sleep(1)

    async def _run(self):
        loop = asyncio.get_running_loop()
        publisher = events.get_publisher(self.app)
        name = self.app['config']['name']  # The unique service name

        self.scanDelegate = ScanDelegate(self.app, loop)
        self.scanner = Scanner().withDelegate(
            self.scanDelegate)

        LOGGER.info('Started TiltScanner')

        while True:
            try:
                await loop.run_in_executor(
                    None, self._blockingScanner)

                message = self.scanDelegate.popMessage()
                if message != {}:
                    LOGGER.debug(message)
                    await publisher.publish(
                        exchange='brewcast',  # brewblox-history's exchange'
                        routing=name,
                        message=message)

            except CancelledError:
                break

            # All other errors are still errors - something bad happened
            # Wait a second, and then continue running
            except Exception as ex:
                LOGGER.error(f'Encountered an error: {ex}')
                sleep(1)

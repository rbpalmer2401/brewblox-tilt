"""
Brewblox service for Tilt hydrometer
"""
import asyncio
from pint import UnitRegistry
from bluepy.btle import Scanner, DefaultDelegate
from aiohttp import web
from brewblox_service import brewblox_logger, events, scheduler, service

routes = web.RouteTableDef()
LOGGER = brewblox_logger("brewblox_tilt")
HISTORY_EXCHANGE = 'brewcast'
ureg = UnitRegistry()
Q_ = ureg.Quantity


class ScanDelegate(DefaultDelegate):
    def __init__(self, publisher, loop):
        self.publisher = publisher
        self.loop = loop
        DefaultDelegate.__init__(self)

    def decodeData(self, data):
        # Tilt uses a similar data layout to iBeacons accross manufacturer data
        # hex digits 8 - 50. Digits 8-40 contain the ID of the "colour" of the
        # device. Digits 40-44 contain the temperature in f as an integer.
        # Digits 44-48 contain the specific gravity * 1000 (i.e. the "points)
        # as an integer.

        ids = {
            "a495bb10c5b14b44b5121370f02d74de": "Red",
            "a495bb20c5b14b44b5121370f02d74de": "Green",
            "a495bb30c5b14b44b5121370f02d74de": "Black",
            "a495bb40c5b14b44b5121370f02d74de": "Purple",
            "a495bb50c5b14b44b5121370f02d74de": "Orange",
            "a495bb60c5b14b44b5121370f02d74de": "Blue",
            "a495bb70c5b14b44b5121370f02d74de": "Yellow",
            "a495bb80c5b14b44b5121370f02d74de": "Pink"
        }

        uuid = data[8:40]
        colour = ids.get(uuid, None)

        temp_f = int(data[40:44], 16)

        raw_sg = int(data[44:48], 16)
        sg = raw_sg/1000

        return {
            "colour": colour,
            "temp_f": temp_f,
            "sg": sg
        }

    def handleData(self, data, rssi):
        decodedData = self.decodeData(data)
        temp_c = Q_(decodedData["temp_f"], ureg.degF).to('degC').magnitude

        # Calback is from sync code so we need to wrap publish back up in the
        # async loop
        asyncio.ensure_future(
            self.publisher.publish(
                HISTORY_EXCHANGE,
                "tilt.{}".format(decodedData["colour"]),
                {
                    'Temperature[degF]': decodedData["temp_f"],
                    'Temperature[degC]': temp_c,
                    'Specific gravity': decodedData["sg"],
                    'Signal strength[dBm]': rssi
                }),
            loop=self.loop)

        LOGGER.info("colour: {}, temp: {}, sg: {}, signal strenght:{}".format(
            decodedData["colour"],
            decodedData["temp_f"],
            decodedData["sg"],
            rssi))

    def handleDiscovery(self, dev, isNewDev, isNewData):
        data = {}
        for (adtype, desc, value) in dev.getScanData():
            data[desc] = value

        # Check if message is from a tilt device
        if data.get("Complete Local Name", None) == "Tilt":
            # Check if Manufacturer data exists (it doesn't always)
            if "Manufacturer" in data:
                self.handleData(data["Manufacturer"], dev.rssi)


class TiltScanner():
    def __init__(self, app):
        self.publisher = events.get_publisher(app)
        self.scanner = None
        self.running = False

    async def stop(self, app):
        self.running = False

    def blockingScanner(self):
        # In theory, this could just be a single start() & multiple process()
        # Unfortunately, that seems less reliable at returning data.
        # The Tilt updates every 5s so we just run a 5sec scan repeatedly.
        # This seems pretty reliable
        while self.running:
            self.scanner.scan(timeout=5)

    async def run(self, app):
        self.running = True
        loop = asyncio.get_running_loop()
        self.scanner = Scanner().withDelegate(
            ScanDelegate(self.publisher, loop))
        await loop.run_in_executor(
            None, self.blockingScanner)


def add_events(app: web.Application):
    # Enable the task scheduler
    # This is required for the `events` feature
    scheduler.setup(app)

    # Enable event handling
    # Event subscription / publishing will be enabled after you call this function
    events.setup(app)


def main():
    app = service.create_app(default_name='tilt')

    # Init events
    add_events(app)

    # Add all default endpoints, and adds prefix to all endpoints
    #
    # Default endpoints are:
    # {prefix}/api/doc (Swagger documentation of endpoints)
    # {prefix}/_service/status (Health check: this endpoint is called to check service status)
    #
    # The prefix is automatically added for all endpoints. You don't have to do anything for this.
    # To change the prefix, you can use the --name command line argument.
    #
    # See brewblox_service.service for more details on how arguments are parsed.
    service.furnish(app)

    tiltScan = TiltScanner(app)
    app.on_startup.append(tiltScan.run)
    app.on_cleanup.append(tiltScan.stop)

    # service.run() will start serving clients async
    service.run(app)


if __name__ == '__main__':
    main()

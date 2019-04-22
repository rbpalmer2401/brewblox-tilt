# BrewBlox Service for the Tilt Hydrometer

The [Tilt hydrometer](https://tilthydrometer.com/) is a wireless hydrometer and thermometer used to gather live readings of specific gravity and temperature when brewing beer.

[Brewblox](https://brewpi.com/) is a modular brewery control system design to work with the BrewPi controller.

This brewblox service integrates the Tilt hydrometer into Brewblox.

## Usage

### Deploy the Tilt service on the BrewBlox stack

You need to add the service to your existing BrewBlox docker compose file.

```yaml
tilt:
    image: j616s/brewblox-tilt:rpi-latest
    restart: unless-stopped
    privileged: true
    depends_on:
        - history
    network_mode: host
    command: -p 5001 --eventbus-host=172.17.0.1
```

The brewblox-tilt docker images are available on docker hub.

Note that the image tag to use is:

-   rpi-latest for the arm architecture (when deploying on a RaspberryPi)
-   latest for the amd architecture

You'll also need to modify the eventbus entry in your existing BrewBlox docker compose file to look like this.

```yaml
eventbus:
    image: arm32v6/rabbitmq:alpine
    restart: unless-stopped
    ports:
        - "5672:5672"
```

Finally, you'll have to bring up the new service using

```bash
brewblox-ctl up
```

### Add to your graphs

Once the Tilt service receives data from your Tilt(s), it should be available as graph metrics in brewblox.

## Development

You can build a docker container for x86 using the following:

```bash
bbt-localbuild
```

Or for ARM using the following:

```bash
bbt-localbuild --arch arm
```

You can then run this container using the following:

```bash
docker run --net=host --privileged j616s/brewblox-tilt:local
```

## TODO

-   Allow calibration of temperature and SG values

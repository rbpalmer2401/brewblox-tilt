# BrewBlox Service for the Tilt Hydrometer

**This service is work in progress and is not currently functional**

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
    labels:
        - "traefik.port=5000"
        - "traefik.frontend.rule=PathPrefix: /tilt"
    network_mode: host
```

The brewblox-tilt docker images are available on docker hub.

Note that the image tag to use is:

-   rpi-latest for the arm architecture (when deploying on a RaspberryPi)
-   latest for the amd architecture

### Add to your graphs

Once the Tilt service receives data from your Tilt(s), it should be available as graph metrics in brewblox.

## TODO

-   Allow calibration of temperature and SG values

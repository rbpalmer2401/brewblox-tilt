"""
Brewblox service for Tilt hydrometer
"""
from brewblox_service import events, scheduler, service
from brewblox_tilt import tiltScanner


def main():
    app = service.create_app(default_name='tilt')

    # Both tiltScanner and event handling requires the task scheduler
    scheduler.setup(app)

    # Initialize event handling
    events.setup(app)

    # Initialize your feature
    tiltScanner.setup(app)

    # Add all default endpoints
    service.furnish(app)

    # service.run() will start serving clients async
    service.run(app)


if __name__ == '__main__':
    main()

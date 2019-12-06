#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convenience installation script for adding a Tilt service to a BrewBlox installation.

It must be run in the BrewBlox install directory.

To run:

    python3 install_tilt.py

Steps:
- Creates a calibration dir with the same name as the service.
- Append the tilt service to ./docker-compose.yml.
- Modify the eventbus service to publish port 5672 on the host.

Notes:
- Python >= 3.5 is required to run.
- This scripts depends on packages also used by brewblox-ctl
    - pyyaml
    - click
- No calibration files are added or modified.
"""

import re
from os import makedirs, path
from platform import machine
from subprocess import check_call

import click
import yaml


def _validate_name(ctx, param, value):
    if not re.match(r'^[a-z0-9-_]+$', value):
        raise click.BadParameter('Names can only contain letters, numbers, - or _')
    return value


@click.command()
@click.option('-n', '--name',
              prompt='How do you want to call this service? The name must be unique',
              default='tilt',
              callback=_validate_name,
              help='Service name')
@click.option('--port',
              type=int,
              default=5001,
              help='Service port - must be unused, as this service runs on the host')
@click.option('-f', '--force',
              is_flag=True,
              help='Allow overwriting an existing service')
def install(name, port, force):
    """
    Install Tilt Service for BrewBlox

    Creates an empty configuration dir with the same name as the service.
    If you want to calibrate your tilt, place the calibration files in this directory.
    """
    tilt_dir = path.abspath('./' + name)
    compose_file = path.abspath('./docker-compose.yml')

    if not path.exists(compose_file):
        raise SystemExit('ERROR: Compose file not found in current directory. '
                         'Please navigate to your brewblox directory first.')

    print('Creating ./{} directory...'.format(name))
    if not path.exists(tilt_dir):
        makedirs(tilt_dir)

    print('Editing docker-compose.yml file...')
    with open(compose_file) as f:
        config = yaml.safe_load(f)

    if name in config['services'] and not force:
        print('Service "{}" already exists. Use the --force flag if you want to overwrite it'.format(name))
        return

    tag = 'rpi-latest' if machine().startswith('arm') else 'latest'

    config['services'][name] = {
        'image': 'j616s/brewblox-tilt:{}'.format(tag),
        'restart': 'unless-stopped',
        'privileged': True,
        'network_mode': 'host',
        'command': '--name {} --port {} --eventbus-host=172.17.0.1'.format(name, port),
        'volumes': ['./{}:/share'.format(name)]
    }
    config['services']['eventbus']['ports'] = ['5672:5672']

    with open(compose_file, 'w') as f:
        yaml.safe_dump(config, f)

    print('Starting services...')
    check_call('brewblox-ctl up', shell=True)


if __name__ == '__main__':
    install()

#!/usr/bin/python3
'''
    Firmware Analysis and Comparison Tool (FACT)
    Copyright (C) 2015-2018  Fraunhofer FKIE

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import logging
import sys

from helperFunctions.web_interface import ConnectTo
from storage.db_interface_backend import BackEndDbInterface
from helperFunctions.program_setup import program_setup


PROGRAM_NAME = 'FACT Database Migration Helper'
PROGRAM_DESCRIPTION = 'Migrate FACT\'s Database from an old version'


def main(command_line_options=sys.argv):
    _, config = program_setup(PROGRAM_NAME, PROGRAM_DESCRIPTION, command_line_options=command_line_options)

    logging.info('Trying to start Mongo Server and initializing users...')
    with ConnectTo(BackEndDbInterface, config) as db_service:
        firmwares = db_service.firmwares.find()
        for f in firmwares:
            db_service.firmware_metadata

    return 0


if __name__ == '__main__':
    sys.exit(main())

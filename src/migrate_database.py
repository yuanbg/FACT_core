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
from typing import Iterable

import pymongo

from helperFunctions.dataConversion import convert_time_to_str
from helperFunctions.program_setup import program_setup
from helperFunctions.web_interface import ConnectTo
from objects.firmware import Firmware
from storage.db_interface_backend import BackEndDbInterface


PROGRAM_NAME = 'FACT Database Migration Helper'
PROGRAM_DESCRIPTION = 'Migrate FACT\'s Database from an old version'


def main():
    _, config = program_setup(PROGRAM_NAME, PROGRAM_DESCRIPTION, command_line_options=sys.argv)

    logging.info('Trying to migrate MongoDB')
    with ConnectTo(BackEndDbInterface, config) as db_service:  # type: BackEndDbInterface
        collection = db_service.main.firmwares  # type: pymongo.collection.Collection
        firmwares = collection.find()  # type: Iterable[dict]
        for firmware in firmwares:
            firmware_object = convert_to_firmware(firmware, db_service)
            db_service.add_firmware(firmware_object)
    return 0


def convert_to_firmware(entry, db_service, analysis_filter=None) -> Firmware:
    firmware = Firmware()
    firmware.uid = entry['_id']
    firmware.size = entry['size']
    firmware.set_name(entry['file_name'])
    firmware.set_device_name(entry['device_name'])
    firmware.set_device_class(entry['device_class'])
    firmware.set_release_date(convert_time_to_str(entry['release_date']))
    firmware.set_vendor(entry['vendor'])
    firmware.set_firmware_version(entry['version'])
    firmware.processed_analysis = db_service.retrieve_analysis(entry['processed_analysis'], analysis_filter=analysis_filter)
    firmware.files_included = set(entry['files_included'])
    firmware.virtual_file_path = entry['virtual_file_path']
    firmware.tags = entry['tags'] if 'tags' in entry else dict()
    firmware.analysis_tags = entry['analysis_tags'] if 'analysis_tags' in entry else dict()

    for key, default in [('comments', []), ('device_part', 'complete')]:  # for backwards compatibility
        setattr(firmware, key, entry[key] if key in entry else default)
    return firmware


if __name__ == '__main__':
    sys.exit(main())

import logging
import sys
from time import time
from typing import Union

from helperFunctions.dataConversion import convert_str_to_time
from helperFunctions.object_storage import (
    update_analysis_tags, update_included_files, update_virtual_file_path
)
from helperFunctions.tag import update_tags
from objects.file import FileObject
from objects.firmware import Firmware
from pymongo.errors import PyMongoError
from storage.db_interface_common import MongoInterfaceCommon


class BackEndDbInterface(MongoInterfaceCommon):

    def add_object(self, fo_fw: Union[FileObject, Firmware]):
        if isinstance(fo_fw, Firmware):
            self.add_firmware(fo_fw)
        elif isinstance(fo_fw, FileObject):
            self.add_file_object(fo_fw)
        else:
            logging.error('invalid object type: {} -> {}'.format(type(fo_fw), fo_fw))
            return
        self.release_unpacking_lock(fo_fw.uid)

    def update_object(self, new_object: Union[FileObject, Firmware], old_object: dict):
        update_dictionary = {
            'processed_analysis': self._update_processed_analysis(new_object, old_object),
            'files_included': update_included_files(new_object, old_object),
            'virtual_file_path': update_virtual_file_path(new_object, old_object),
            'analysis_tags': update_analysis_tags(new_object, old_object),
            'parent_firmware_uids': list(set.union(set(old_object['parent_firmware_uids']),
                                                   new_object.parent_firmware_uids)),
        }
        self.file_objects.update_one({'_id': new_object.get_uid()}, {'$set': update_dictionary})

    def update_firmware_metadata(self, firmware: Firmware):
        update_dictionary = {
            'version': firmware.version,
            'device_name': firmware.device_name,
            'device_part': firmware.part,
            'device_class': firmware.device_class,
            'vendor': firmware.vendor,
            'release_date': convert_str_to_time(firmware.release_date),
            'tags': firmware.tags,
        }
        self.firmware_metadata.update_one({'uid': firmware.uid}, {'$set': update_dictionary})

    def _update_processed_analysis(self, new_object: FileObject, old_object: dict) -> dict:
        old_pa = self.retrieve_analysis(old_object['processed_analysis'])
        for key in new_object.processed_analysis.keys():
            old_pa[key] = new_object.processed_analysis[key]
        return self.sanitize_analysis(analysis_dict=old_pa, uid=new_object.get_uid())

    def add_firmware(self, firmware: Firmware):
        old_object = self.file_objects.find_one({'_id': firmware.get_uid()})
        if old_object:
            logging.debug('Update old firmware!')
            try:
                self.update_object(new_object=firmware, old_object=old_object)
                self.update_firmware_metadata(firmware)
            except Exception as e:
                logging.error('[{}] Could not update firmware: {}'.format(type(e), e))
                return None
        else:
            logging.debug('Detected new firmware!')
            fo_entry = self.build_file_object_dict(firmware)
            metadata_entry = self.build_firmware_metadata_dict(firmware)
            try:
                self.file_objects.insert_one(fo_entry)
                self.firmware_metadata.insert_one(metadata_entry)
                logging.debug('firmware added to db: {}'.format(firmware.get_uid()))
            except Exception as e:
                logging.error('Could not add firmware: {} - {}'.format(sys.exc_info()[0].__name__, e))
                return None

    @staticmethod
    def build_firmware_metadata_dict(firmware: Firmware):
        entry = {
            'device_class': firmware.device_class,
            'device_name': firmware.device_name,
            'device_part': firmware.part,
            'md5': firmware.md5,
            'release_date': convert_str_to_time(firmware.release_date),
            'submission_date': time(),
            'tags': firmware.tags,
            'uid': firmware.uid,
            'vendor': firmware.vendor,
            'version': firmware.version,
        }
        return entry

    def add_file_object(self, file_object):
        old_object = self.file_objects.find_one({'_id': file_object.get_uid()})
        if old_object:
            logging.debug('Update old file_object!')
            try:
                self.update_object(new_object=file_object, old_object=old_object)
            except Exception as e:
                logging.error('[{}] Could not update file object: {}'.format(type(e), e))
                return None
        else:
            logging.debug('Detected new file_object!')
            entry = self.build_file_object_dict(file_object)
            try:
                self.file_objects.insert_one(entry)
                logging.debug('file added to db: {}'.format(file_object.get_uid()))
            except Exception as e:
                logging.error('Could not update firmware: {} - {}'.format(sys.exc_info()[0].__name__, e))
                return None

    def build_file_object_dict(self, file_object: Union[FileObject, Firmware]):
        analysis = self.sanitize_analysis(analysis_dict=file_object.processed_analysis, uid=file_object.get_uid())
        entry = {
            '_id': file_object.get_uid(),
            'analysis_tags': file_object.analysis_tags,
            'comments': file_object.comments,
            'depth': file_object.depth,
            'file_name': file_object.file_name,
            'file_path': file_object.file_path,
            'files_included': list(file_object.files_included),
            'is_firmware': file_object.is_firmware,
            'parent_firmware_uids': list(file_object.parent_firmware_uids),
            'parents': file_object.parents,
            'processed_analysis': analysis,
            'sha256': file_object.sha256,
            'size': file_object.size,
            'virtual_file_path': file_object.virtual_file_path,
        }
        return entry

    def _convert_to_firmware(self, entry, analysis_filter=None):
        firmware = super()._convert_to_firmware(entry, analysis_filter=None)
        firmware.set_file_path(entry['file_path'])
        return firmware

    def _convert_to_file_object(self, entry, analysis_filter=None):
        file_object = super()._convert_to_file_object(entry, analysis_filter=None)
        file_object.set_file_path(entry['file_path'])
        return file_object

    def update_analysis_tags(self, uid, plugin_name, tag_name, tag):
        firmware_object = self.get_object(uid=uid, analysis_filter=[])
        try:
            tags = update_tags(firmware_object.analysis_tags, plugin_name, tag_name, tag)
        except ValueError as value_error:
            logging.error('Plugin {} tried setting a bad tag {}: {}'.format(plugin_name, tag_name, str(value_error)))
            return None
        except AttributeError:
            logging.error('Firmware not in database yet: {}'.format(uid))
            return None

        if isinstance(firmware_object, Firmware):
            try:
                self.firmwares.update_one({'_id': uid}, {'$set': {'analysis_tags': tags}})
            except (TypeError, ValueError, PyMongoError) as exception:
                logging.error('Could not update firmware: {} - {}'.format(type(exception), str(exception)))
        else:
            logging.warning('Propagating tag only allowed for firmware. Given: {}')

    def add_analysis(self, file_object: Union[FileObject, Firmware]):
        if isinstance(file_object, (Firmware, FileObject)):
            processed_analysis = self.sanitize_analysis(file_object.processed_analysis, file_object.get_uid())
            for analysis_system in processed_analysis:
                self._update_analysis(file_object, analysis_system, processed_analysis[analysis_system])
        else:
            raise RuntimeError('Trying to add from type \'{}\' to database. Only allowed for \'Firmware\' and \'FileObject\'')

    def _update_analysis(self, file_object: Union[FileObject, Firmware], analysis_system: str, result: dict):
        try:
            entry_with_tags = self.file_objects.find_one({'_id': file_object.uid}, {'analysis_tags': 1})

            self.file_objects.update_one(
                {'_id': file_object.get_uid()},
                {'$set': {
                    'processed_analysis.{}'.format(analysis_system): result,
                    'analysis_tags': update_analysis_tags(file_object, entry_with_tags)
                }}
            )
        except Exception as exception:
            logging.error('Update of analysis failed badly ({})'.format(exception))
            raise exception

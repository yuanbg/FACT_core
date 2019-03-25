import logging
import sys
from typing import Union, List

from pymongo.errors import PyMongoError

from helperFunctions.compare_sets import remove_duplicates_from_list
from helperFunctions.object_storage import update_analysis_tags, update_included_files, update_virtual_file_path
from helperFunctions.tag import update_tags
from objects.file import FileObject
from objects.firmware import Firmware
from storage.db_interface_common import MongoInterfaceCommon


class BackEndDbInterface(MongoInterfaceCommon):

    def add_object(self, fo: FileObject):
        self.add_file_object(fo)
        self.release_unpacking_lock(fo.uid)

    def update_object(self, new_object: FileObject, old_object: dict):
        update_dictionary = {
            'processed_analysis': self._update_processed_analysis(new_object, old_object),
            'files_included': update_included_files(new_object, old_object),
            'virtual_file_path': update_virtual_file_path(new_object, old_object),
            'analysis_tags': update_analysis_tags(new_object, old_object),
            'parent_firmware_uids': remove_duplicates_from_list(old_object['parent_firmware_uids'], new_object.parent_firmware_uids),
            'is_root': new_object.is_root,
        }
        self.file_objects.update_one({'_id': new_object.get_uid()}, {'$set': update_dictionary})

    def _update_processed_analysis(self, new_object: FileObject, old_object: dict) -> dict:
        old_pa = self.retrieve_analysis(old_object['processed_analysis'])
        for key in new_object.processed_analysis.keys():
            old_pa[key] = new_object.processed_analysis[key]
        return self.sanitize_analysis(analysis_dict=old_pa, uid=new_object.get_uid())

    def add_file_object(self, file_object: FileObject):
        old_object = self.file_objects.find_one({'_id': file_object.get_uid()})
        if old_object:
            logging.debug('Update old file_object!')
            try:
                self.update_object(new_object=file_object, old_object=old_object)
            except Exception as exception:
                logging.error('[{}] Could not update file object: {}'.format(type(exception), exception))
        else:
            logging.debug('Detected new file_object!')
            entry = self.build_file_object_dict(file_object)
            try:
                self.file_objects.insert_one(entry)
                logging.debug('file added to db: {}'.format(file_object.get_uid()))
            except Exception as exception:
                logging.error('Could not update firmware: {} - {}'.format(sys.exc_info()[0].__name__, exception))

    def build_file_object_dict(self, file_object: Union[FileObject, Firmware]) -> dict:
        analysis = self.sanitize_analysis(analysis_dict=file_object.processed_analysis, uid=file_object.get_uid())
        entry = {
            '_id': file_object.get_uid(),
            'analysis_tags': file_object.analysis_tags,
            'comments': file_object.comments,
            'depth': file_object.depth,
            'file_name': file_object.file_name,
            'file_path': file_object.file_path,
            'files_included': list(file_object.files_included),
            'is_root': file_object.is_root,
            'parent_firmware_uids': list(file_object.parent_firmware_uids),
            'parents': file_object.parents,
            'processed_analysis': analysis,
            'sha256': file_object.sha256,
            'size': file_object.size,
            'virtual_file_path': file_object.virtual_file_path,
        }
        return entry

    def _convert_to_file_object(self, entry, analysis_filter=None):
        file_object = super()._convert_to_file_object(entry, analysis_filter=None)
        file_object.set_file_path(entry['file_path'])
        return file_object

    def update_analysis_tags(self, uid, plugin_name, tag_name, tag):
        file_object = self.get_object(uid=uid, analysis_filter=[])
        if not file_object:
            logging.warning('Object not found while trying to set tag: {}'.format(uid))
        elif not file_object.is_root:
            logging.warning('Propagating tag only allowed for firmware. Given: {}'.format(uid))
        else:
            firmware_list = self.get_all_firmwares_for_uid(uid)
            for firmware in firmware_list:
                self._update_analysis_tags_of_firmware(firmware, plugin_name, tag, tag_name)

    def _update_analysis_tags_of_firmware(self, firmware, plugin_name, tag, tag_name):
        try:
            tags = update_tags(firmware.analysis_tags, plugin_name, tag_name, tag)
        except ValueError as value_error:
            logging.error('Plugin {} tried setting a bad tag {}: {}'.format(plugin_name, tag_name, str(value_error)))
            return
        except AttributeError:
            logging.error('Could not set tag: object not in database yet: {}'.format(firmware.uid))
            return
        try:
            self.firmware_metadata.update_one({'_id': firmware.firmware_id}, {'$set': {'analysis_tags': tags}})
        except (TypeError, ValueError, PyMongoError) as exception:
            logging.error('Could not update firmware: {} - {}'.format(type(exception), str(exception)))

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

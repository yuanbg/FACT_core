import logging
from pathlib import Path

from common_helper_files import get_binary_from_file

from tempfile import TemporaryDirectory
from helperFunctions.web_interface import ConnectTo
from storage.db_interface_common import MongoInterfaceCommon
from unpacker.tar_repack import TarRepack


class BinaryService(object):
    '''
    This is a binary and database backend providing basic return functions
    '''

    def __init__(self, config=None):
        self.config = config
        logging.info("binary service online")

    def get_binary_and_file_name(self, uid):
        tmp = self._get_file_name_and_path_from_db(uid)
        if tmp is None:
            return None, None
        else:
            binary = get_binary_from_file(tmp['file_path'])
            return (binary, tmp['file_name'])

    def get_repacked_binary_and_file_name(self, uid):
        tmp = self._get_file_name_and_path_from_db(uid)
        if tmp is None:
            return None, None
        else:
            repack_service = TarRepack(config=self.config)
            tar = repack_service.tar_repack(tmp['file_path'])
            name = "{}.tar.gz".format(tmp['file_name'])
            return (tar, name)

    def _get_file_name_and_path_from_db(self, uid):
        with ConnectTo(BinaryServiceDbInterface, self.config) as db:
            tmp = db.get_file_name_and_path(uid)
            return tmp

    def get_unpacked_firmware(self, uid):
        archive_directory = TemporaryDirectory(prefix='FACT_fw_download_')
        root_path = Path(archive_directory.name)
        with ConnectTo(MongoInterfaceCommon, self.config) as db:
            firmware = db.get_firmware(uid=uid, analysis_filter=[])
            if firmware is not None:
                self.test_create_extraction_folder(root_path, firmware['file_name'])
                # ToDo extract and recurse

    @staticmethod
    def create_extraction_folder(root_path: Path, file_name: str) -> Path:
        extraction_path = Path(root_path, '{}_extracted'.format(file_name))
        extraction_path.mkdir(parents=True, exist_ok=True)
        return extraction_path


class BinaryServiceDbInterface(MongoInterfaceCommon):

    READ_ONLY = True

    def get_file_name_and_path(self, uid):
        result = self.firmwares.find_one({"_id": uid}, {'file_name': 1, 'file_path': 1})
        if result is None:
            result = self.file_objects.find_one({"_id": uid}, {'file_name': 1, 'file_path': 1})
        return result

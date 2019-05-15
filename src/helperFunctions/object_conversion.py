from objects.file import FileObject
from objects.firmware import Firmware


def create_fw_meta_dict(fw: Firmware) -> dict:
    meta = {
        'device_name': fw.device_name,
        'device_class': fw.device_class,
        'device_part': fw.device_part,
        'vendor': fw.vendor,
        'version': fw.version,
        'release_date': fw.release_date,
        'hid': fw.hid
    }
    return meta


def create_fo_meta_dict(fo: FileObject) -> dict:
    meta = {
        'firmwares_including_this_file': list(fo.get_virtual_file_paths().keys()),
        'virtual_file_path': fo.get_virtual_paths_for_one_uid(),
        'hid': fo.get_hid(),
        'size': fo.size
    }
    if isinstance(fo.list_of_all_included_files, list):
        meta['number_of_files'] = len(fo.list_of_all_included_files)
    return meta

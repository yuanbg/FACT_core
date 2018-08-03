from tempfile import TemporaryDirectory
from storage.binary_service import BinaryService


def test_create_extraction_folder():
    tmp_dir = TemporaryDirectory(prefix='FACT_test_')
    root_path = tmp_dir.name
    bs = BinaryService(config=None)
    extraction_folder = bs.create_extraction_folder(root_path, 'test_file')
    assert extraction_folder.exists()
    assert extraction_folder.__str__() == '{}/test_file_extracted'.format(root_path)
    tmp_dir.cleanup()

from test.common_helper import create_test_file_object, create_test_firmware


class TestVirtualFilePath:  # pylint: disable=no-self-use

    def test_add_file_object(self):
        _, root = create_test_firmware()
        assert root.virtual_file_path[root.get_uid()], [root.get_uid()] == 'virtual file path of root file not correct'
        child_one = create_test_file_object()
        root.add_included_file(child_one)
        child_two = create_test_file_object(bin_path='get_files_test/testfile2')
        root.add_included_file(child_two)
        child_of_child_one = create_test_file_object(bin_path='get_files_test/testfile2')
        child_one.add_included_file(child_of_child_one)
        assert root.get_uid() in child_one.virtual_file_path.keys(), 'no virtual file path for root available'
        assert child_one.virtual_file_path[root.get_uid()][0] == '{}|{}'.format(root.get_uid(), child_one.file_path), 'virtual file path not correct'
        assert child_of_child_one.virtual_file_path[root.get_uid()][0] == '{}|{}|{}'.format(root.get_uid(), child_one.get_uid(), child_of_child_one.file_path)

    def test_add_file_object_path_already_present(self):
        _, root = create_test_firmware()
        child = create_test_file_object()
        child.virtual_file_path = {root.get_uid(): ['{}|some/known/path'.format(root.get_uid())]}
        root.add_included_file(child)
        assert len(child.virtual_file_path.keys()) == 1, 'there should be just one root object'
        assert len(child.virtual_file_path[root.get_uid()]) == 1, 'number of pathes should be one'

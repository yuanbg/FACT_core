from storage.db_interface_common import MongoInterfaceCommon
from pymongo.collection import Collection


class FrontendEditingDbInterface(MongoInterfaceCommon):

    READ_ONLY = False

    def add_comment_to_object(self, uid, comment, author, time):
        self.add_element_to_array_in_field(
            uid, 'comments', {'author': author, 'comment': comment, 'time': str(time)}
        )

    def add_element_to_array_in_field(self, uid, field, element):
        self._get_collection(uid).update_one(
            {'$or': [{'uid': uid}, {'_id': uid}]},
            {'$push': {field: element}}
        )

    def delete_comment(self, uid, timestamp):
        self.remove_element_from_array_in_field(uid, 'comments', {'time': timestamp})

    def remove_element_from_array_in_field(self, uid, field, condition):
        self._get_collection(uid).update_one(
            {'$or': [{'uid': uid}, {'_id': uid}]},
            {'$pull': {field: condition}}
        )

    def _get_collection(self, id_: str) -> Collection:
        if self.is_firmware_id(id_):
            return self.firmware_metadata
        return self.file_objects

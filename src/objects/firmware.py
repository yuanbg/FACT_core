from contextlib import suppress

from helperFunctions.hash import get_md5
from helperFunctions.tag import TagColor


class Firmware:  # pylint: disable=too-many-instance-attributes,too-many-arguments
    '''
    This objects represents a firmware
    '''

    def __init__(self, firmware_id=None, device_name=None, version=None, device_class=None, vendor=None,
                 release_date=None, uid=None):
        self.device_name = device_name
        self.version = version
        self.device_class = device_class
        self.vendor = vendor
        self.release_date = release_date
        self._device_part = ''
        self.md5 = None
        self.tags = {}
        self.analysis_tags = {}
        self.uid = uid
        self.comments = []
        self._firmware_id = firmware_id
        self._hid = None

    @property
    def device_part(self):
        return self._device_part

    @device_part.setter
    def device_part(self, part):
        if part == 'complete':
            self._device_part = ''
        else:
            self._device_part = part

    def set_tag(self, tag, tag_color=TagColor.GRAY):
        self.tags[tag] = tag_color

    def remove_tag(self, tag):
        with suppress(KeyError):
            self.tags.pop(tag)

    @property
    def hid(self):
        '''
        human readable identifier
        '''
        if not self._hid:
            part = ' - {}'.format(self.device_part) if self.device_part else ''
            self._hid = '{} {}{} v. {}'.format(self.vendor, self.device_name, part, self.version)
        return self._hid

    @property
    def firmware_id(self):
        if self._firmware_id is None:
            self._firmware_id = 'F_{}'.format(get_md5(self.hid + self.uid))
        return self._firmware_id

    def __repr__(self):
        return 'Firmware({device_class} {vendor} {device_name} v. {version})'.format(**self.__dict__)

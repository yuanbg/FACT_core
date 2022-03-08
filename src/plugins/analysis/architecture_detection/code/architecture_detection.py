from typing import Dict

from analysis.PluginBase import AnalysisBasePlugin
from storage.fsorganizer import FSOrganizer

try:
    from ..internal import dt, elf, kconfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent / 'internal'))
    import kconfig

    import dt
    import elf
    sys.path.pop()


class AnalysisPlugin(AnalysisBasePlugin):
    '''
    Generically detected target architecture for firmware images.
    '''
    NAME = 'cpu_architecture'
    DEPENDENCIES = ['file_type', 'kernel_config', 'device_tree']
    DESCRIPTION = 'identify CPU architecture'
    VERSION = '0.4.0'
    MIME_BLACKLIST = [
        'application/msword',
        'application/pdf',
        'application/postscript',
        'application/x-dvi',
        'application/x-httpd-php',
        'application/xhtml+xml',
        'application/xml',
        'image',
        'video',
    ]

    def __init__(self, plugin_administrator, config=None, recursive=True):
        self.config = config
        self._fs_organizer = FSOrganizer(config)
        super().__init__(plugin_administrator, config=config, recursive=recursive, plugin_path=__file__)

    def process_object(self, file_object):
        arch_dict = construct_result(file_object, self._fs_organizer)
        file_object.processed_analysis[self.NAME]['architectures'] = arch_dict
        file_object.processed_analysis[self.NAME]['summary'] = list(arch_dict.keys())

        return file_object


class MetaDataDetector:
    '''
    Architecture detection based on metadata
    '''

    architectures = {
        'ARC': ['ARC Cores'],
        'ARM': ['ARM'],
        'AVR': ['Atmel AVR'],
        'PPC': ['PowerPC', 'PPC'],
        'MIPS': ['MIPS'],
        'x86': ['x86', '80386', '80486'],
        'SPARC': ['SPARC'],
        'RISC-V': ['RISC-V'],
        'RISC': ['RISC', 'RS6000', '80960', '80860'],
        'S/390': ['IBM S/390'],
        'SuperH': ['Renesas SH'],
        'ESP': ['Tensilica Xtensa'],
        'Alpha': ['Alpha'],
        'M68K': ['m68k', '68020'],
        'Tilera': ['TILE-Gx', 'TILE64', 'TILEPro']
    }
    bitness = {
        '8-bit': ['8-bit'],
        '16-bit': ['16-bit'],
        '32-bit': ['32-bit', 'PE32', 'MIPS32'],
        '64-bit': ['64-bit', 'aarch64', 'x86-64', 'MIPS64', '80860']
    }
    endianness = {
        'little endian': ['LSB', '80386', '80486', 'x86'],
        'big endian': ['MSB']
    }

    def get_device_architecture(self, file_object):
        type_of_file = file_object.processed_analysis['file_type']['full']
        arch_dict = file_object.processed_analysis.get('cpu_architecture', dict())
        architecture = self._search_for_arch_keys(type_of_file, self.architectures, delimiter='')
        if not architecture:
            return arch_dict
        bitness = self._search_for_arch_keys(type_of_file, self.bitness)
        endianness = self._search_for_arch_keys(type_of_file, self.endianness)
        full_isa_result = f'{architecture}{bitness}{endianness} (M)'
        arch_dict.update({full_isa_result: 'Detection based on meta data'})
        return arch_dict

    @staticmethod
    def _search_for_arch_keys(file_type_output, arch_dict, delimiter=', '):
        for key in arch_dict:
            for bit in arch_dict[key]:
                if bit in file_type_output:
                    return delimiter + key
        return ''


metadata_detector = MetaDataDetector()


def construct_result(file_object, fs_organizer) -> Dict[str,  str]:
    """
    Returns a dict where keys are the architecture and values are the means of
    detection
    """
    result = {}
    result.update(dt.construct_result(file_object))
    result.update(kconfig.construct_result(file_object))
    result.update(elf.construct_result(file_object, fs_organizer))

    result.update(metadata_detector.get_device_architecture(file_object))

    return result

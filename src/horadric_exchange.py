"""
Python script for exchanging the Horadric Cube contents of two Diablo II characters. Chiefly aiming at legacy v1.12.

Literature:
===========
[1] https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md
  Description of the Diablo 2 save game format.
[2] https://github.com/krisives/d2s-format
  Description of the Diablo 2 save game format.
[3] https://daancoppens.wordpress.com/2017/01/25/understanding-the-diablo-2-save-file-format-part-1/
  This is all about sectioning the entire save game file. Pretty nifty!
[4] https://www.d2mods.info/forum/viewtopic.php?t=9011&start=100
  "It appears that all the "sections" (quests "Woo!", waypoints "WS", npc introductions "w4", stats "gf", skills "if",
  items "JM" (with corpse count etc), and mercenary "jf"->"kf" (with "JM" item list))
   are ..."

Fun facts:
v1.12, which is the one I am interested in has version code "96". More precisely, "96" is for "v1.10 - v1.14d"

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/01/29.
"""

import re
import sys
import argparse
import logging
from argparse import RawTextHelpFormatter
from pathlib import Path
from copy import deepcopy
from shutil import copyfile
from typing import List, Dict, Optional, Union
from enum import Enum


logging.basicConfig(level=logging.INFO, format= '[%(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


class E_Section(Enum):
    """Sections of the save game file."""
    ES_UNSPECIFIED = 0
    ES_HEADER = 1
    ES_QUESTS = 2
    ES_WAYPOINTS = 3
    ES_INTRODUCTIONS = 4
    ES_STATISTICS = 5
    ES_SKILLS = 6
    ES_ITEMS = 7


class E_ItemSites(Enum):
    """Convenience enum for handling item site types."""
    IS_UNSPECIFIED = 0
    IS_INVENTORY = 1
    IS_STASH = 2
    IS_CUBE = 3


class Data:
    """Data object concerned with the binary content of the entirety of a .d2s save game file."""
    def __init__(self, data: bytes):
        self.data = data

    def checksum_reset(self):
        """Sets the checksum to 0. This is necessary before computation of a new checksum."""
        self.data = self.data[0:12] + b'\x00\x00\x00\x00' + self.data[16:]

    def checksum_update(self) -> bytes:
        """Important function! Will update the checksum entry. This is important to be done as final
        step before saving. If the checksum does not reflect the save game file, the game will not accept it.
        :returns the checksum in a 4-byte binary string. Also updates the self.data accordingly."""
        self.checksum_reset()
        csum = 0
        for elt in self.data:
            csum = ((csum << 1) + elt) % 0xffffffff
        csum = csum.to_bytes(4, 'little')
        self.data = self.data[0:12] + csum + self.data[16:]
        return csum

    def get_checksum(self) -> bytes:
        return self.data[12:16]

    def get_name(self, as_str: bool = False) -> Union[bytes, str]:
        """:returns the character name. Either as str or as the 16 byte bytes array."""
        b_name = self.data[20:36]
        return b_name.decode().replace('\x00', '') if as_str else b_name

    def set_name(self, name: str):
        """Sets the given name of maximum length 16."""
        regex = re.compile("^[a-zA-Z_-]{2,}$")
        acceptable = regex.search(name) is not None
        if acceptable:
            n_hyphens = sum([1 if j == '-' else 0 for j in name])
            n_uscores = sum([1 if j == '_' else 0 for j in name])
            if n_hyphens > 1 or n_uscores > 1:
                acceptable = False
        if not acceptable:
            _log.warning(f"New name '{name}' is unacceptable. Ignoring set_name.")
            return
        if len(name) > 15:
            name = name[0:15]
        elif len(name) < 15:
            name += '\x00' * (15 - len(name))
        bname = name.encode() + b'\x00'
        self.data = self.data[0:20] + name.encode() + self.data[36:]

    def get_class(self, as_str: bool = False) -> Union[bytes, str]:
        """:returns this character's class as a byte or string."""
        val = int(self.data[40])
        if not as_str: return val.to_bytes(1, 'little')
        elif val == 0: return "Amazon"
        elif val == 1: return "Sorceress"
        elif val == 2: return "Necromancer"
        elif val == 3: return "Paladin"
        elif val == 4: return "Barbarian"
        elif val == 5: return "Druid"
        elif val == 6: return "Assassin"

    #def is_dead(self) -> bool:
    #    pass

    #def get_items(self) -> Dict[E_ItemSites]:
    #    pass

    def __str__(self) -> str:
        msg = f"{self.get_name(True)}, a level {self.data[43]} {self.get_class(True)}. Checksum: '{int.from_bytes(self.get_checksum(), 'little')}'"
        return msg


class Horadric:
    def __init__(self, args: Optional[List[str]] = None):
        # > Setting up the data. -------------------------------------
        parsed = self.parse_arguments(args)
        pfnames_in = parsed.pfnames  # type: List[str]
        do_backup = not parsed.omit_backup  # type: bool
        if do_backup:
            for pfname in pfnames_in:
                Horadric.do_backup(pfname)
        else:
            print("Omitting backups.")
        data = [Data(Horadric.read_binary_file(pfname)) for pfname in pfnames_in]
        # < ----------------------------------------------------------
        contents_binary_out = Horadric.do_the_exchange(data[0].data, data[1].data)
        contents_binary_out = [Horadric.update_file_size(content) for content in contents_binary_out]
        contents_binary_out = [Horadric.update_checksum(content) for content in contents_binary_out]
        for j in range(2):
            print(data[j])
            Horadric.print_statistics(contents_binary_out[j])
            #Horadric.write_binary_file(pfnames_in[j], contents_binary_out[j])
        pass

    @staticmethod
    def die(msg: str, status: int = 0):
        """Tool function for exiting the script if something goes wrong."""
        print(f"{msg} ({status})")
        sys.exit(status)

    @staticmethod
    def do_backup(pfname: str):
        pfname_backup = pfname + '.backup'
        print(f"Doing backup: '{pfname}' -> '{pfname_backup}'.")
        copyfile(pfname, pfname_backup)

    @staticmethod
    def read_binary_file(pfname: str) -> bytes:
        """Load the entirety of the target file's contents into a byte string."""
        path = Path(pfname)
        if not path.is_file():
            Horadric.die(f"Character file '{pfname}' could not be opened for reading.", 1)
        with open(pfname, mode='rb') as IN:
            return IN.read()

    @staticmethod
    def write_binary_file(pfname: str, data: bytes):
        with open(pfname, mode='wb') as OUT:
            OUT.write(data)
        print(f"Wrote file '{pfname}'.")

    @staticmethod
    def get_checksum(data) -> bytes:
        return data[12:16]

    @staticmethod
    def compute_checksum(data_in: bytes):
        data = data_in[0:12] + b'\x00\x00\x00\x00' + data_in[16:]
        csum = 0
        for elt in data:
            csum = ((csum << 1) + elt) % 0xffffffff
        return csum.to_bytes(4, 'little')

    @staticmethod
    def update_checksum(data_in: bytes) -> bytes:
        csum = Horadric.compute_checksum(data_in)
        data = data_in[0:12] + csum + data_in[16:]
        return data

    @staticmethod
    def get_file_size(data_in: bytes) -> int:
        return int.from_bytes(data_in[8:12], 'little')

    @staticmethod
    def update_file_size(data_in: bytes) -> bytes:
        sz = len(data_in).to_bytes(4, 'little')
        return data_in[0:8] + sz + data_in[12:]

    @staticmethod
    def get_character_name(data_in: bytes) -> str:
        return data_in[20:36].decode().replace('\x00', '')

    @staticmethod
    def set_character_name(data_in: bytes, name: str) -> bytes:
        bname = name.encode('ISO-8859-1')
        bname = bname + b'\x00' * (16 - len(bname))
        return data_in[0:20] + bname + data_in[36:]

    @staticmethod
    def do_the_exchange(data0: bytes, data1: bytes) -> List[bytes]:
        hsi0 = Horadric.get_headerskills_and_items(data0)
        hsi1 = Horadric.get_headerskills_and_items(data1)
        res0 = hsi0[0]
        res1 = hsi1[0]
        return [res0 + b'JM\x00\x00JM\x00\x00', res1 + b'JM\x00\x00JM\x00\x00']
        items0_prior = Horadric.parse_items(data0)
        items1_prior = Horadric.parse_items(data1)
        items0 = items0_prior[False]
        #items0.extend(items1_prior[True])
        items1 = items1_prior[False]
        #items1.extend(items0_prior[True])
        for item in items0:
            res0 += item
        for item in items1:
            res1 += item
        return [res0, res1]

    @staticmethod
    def get_headerskills_and_items(data:bytes) -> List[bytes]:
        """:param data: The entirety of a binary .d2s file content.
        :returns A split version of the data block. First entry is the header and skills section.
          Second entry holds the items section."""
        # The file has a header of size 765 bytes. Then 281 bytes for skills. Items may come after that header.
        #return [deepcopy(data[0:(765+281)]), deepcopy(data[(765+281):])]
        #return [deepcopy(data[0:(765+32)]), deepcopy(data[(765+32):])]
        res = data.split(b'JM', 1)
        return [deepcopy(res[0]), deepcopy(b'JM' + res[1])] if len(res) > 1 else [deepcopy(res[0]), list()]

    @staticmethod
    def parse_items(data: bytes) -> Dict[bool, List[bytes]]:
        """Parses for items in the given data blob.
        :param data: Binary string holding the entirety of a .d2s file.
        :returns a dict of True, False. Both entries hold a list of items each.
          False items are non-horadric. True items have been found within the Horadric Cube."""
        res = list()  # type: List[bytes]
        name = data[20:36].decode().replace('\x00', '') # type: str
        # The file has a header of size 765 bytes. Then 281 bytes for skills. Items may come after that header.
        split = Horadric.get_headerskills_and_items(data)
        main = split[1]
        items = main.split(b'JM')
        items = [(b'JM' + item) for item in items]
        # For items that are "stored" a 3-bit integer encoded starting at bit 73 describes where to store the item:
        # Horadric cube: '001' AKA 4 in little endian.
        # [Note: Since the header 'JM' is already dropped, we are looking for bits (57,58,59)
        #  Hence, the following line: The 7th byte leads us to Bit 56. Shift >>1 to reach Bit 57.
        #  Finally bitwise AND the mask 111 to discard all but the first three bits.]
        res = {False: list(), True: list()}  # type: Dict[bool, List[bytes]]
        for item in items:
            if (len(item) <= 9) or (7 & (item[9] >> 1) != 4):
                res[False].append(item)
            else:
                res[True].append(item)
        print(f"For '{name}' found {len(res[True])} horadric cube items and {len(res[False])} otherwisely stored items.")
        return res

    @staticmethod
    def print_statistics(data: bytes):
        print(f"Input file size for '{Horadric.get_character_name(data)}' is {Horadric.get_file_size(data)} bytes. Checksum: {int.from_bytes(Horadric.get_checksum(data))}")

    @staticmethod
    def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
        if args is None:
            args = sys.argv[1:]
        desc = """Exchanges the contents of two Diablo 2 characters' Horadric Cubes.
        
Consider that Barbarian finding the 'sacred globe of divine world domination' that the sorceress has been
looking for all these years. The poor brute does not even know how to equip it to bash a zombie's head in.
And there is just no way to give it to the Sorceress. Sad. Really sad.

No more! The Barbarian may just put the sacred globe into his Horadric Cube!
If she is of the corteous type, the Sorceress may put some glass perls into her Horadric Cube.
Then exit the game and call this Horadric script on the Sorceress' and Barbarian's .d2s save game files.
(Required level not quite known. Python 3.13 should do nicely though.)
The Horadric code lines in this script will then exchange both Horadric Cubes' contents.
Putting the Barbarian's cube's contents into the Sorceress' cube and vice versa."""
        epilog = f"""Example call:
$ python3 {Path(sys.argv[0]).name} conan.d2s ormaline.d2s"""
        parser = argparse.ArgumentParser(prog='Horadric Exchange', description=desc, epilog=epilog, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--omit_backup', action='store_true',
            help="Per default, both .d2s target files will be backupped to .backup files. For safety. This option will disable that safety.")
        parser.add_argument('pfnames', nargs=2, type=str, help='Two positional arguments: Path and filename to first and to second character file.')
        parsed = parser.parse_args(sys.argv[1:])  # type: argparse.Namespace
        return parsed

if __name__ == '__main__':
    hor = Horadric()
    print("Done.")

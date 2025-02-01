"""
Python script for exchanging the Horadric Cube contents of two Diablo II characters. Chiefly aiming at legacy v1.12.

Literature:
===========
[1] https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md
  Description of the Diablo 2 save game format. Quite good. Principal source of information.
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

from __future__ import annotations
import os
import re
import sys
import time
import logging
import argparse
from argparse import RawTextHelpFormatter
from idlelib.stackviewer import VariablesTreeItem
from pathlib import Path
from copy import deepcopy
from shutil import copyfile
from typing import List, Dict, Optional, Union, Tuple
from enum import Enum


logging.basicConfig(level=logging.INFO, format= '[%(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


class E_ItemBlock(Enum):
    """Convenience enum for handling the major item organisation sites.
    https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#items
    [Note: The Header (HD) items are special. They are only treated as items, since they start b'JM', too.]"""
    IB_PLAYER_HD = 0
    IB_PLAYER = 1
    IB_CORPSE_HD = 2
    IB_CORPSE = 3
    IB_MERCENARY_HD = 4
    IB_MERCENARY = 5
    IB_IRONGOLEM_HD = 6
    IB_IRONGOLEM = 7
    IB_UNSPECIFIED = 10


class E_ItemParent(Enum):
    """Bits 58-60 in the item putatively store the major site where the Item is equipped. 
    https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#parent """
    IP_STORED = 0
    IP_EQUIPPED = 1
    IP_BELT = 2
    IP_CURSOR = 4
    IP_ITEM = 6
    IP_UNSPECIFIED = 10


class E_ItemStorage(Enum):
    """Relevant for stored items. Bits 73-75.
    https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#parent """
    IS_INVENTORY = 1
    IS_CUBE =4
    IS_STASH =5
    IS_UNSPECIFIED = 10


class E_ItemEquipment(Enum):
    """Relevant for equipped items.
    https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#parent """
    IE_UNSPECIFIED = 0
    IE_HELMET = 1
    IE_AMULET = 2
    IE_ARMOR = 3
    IE_WEAPON_RIGHT = 4
    IE_WEAPON_LEFT = 5
    IE_RING_RIGHT = 6
    IE_RING_LEFT = 7
    IE_BELT = 8
    IE_BOOTS = 9
    IE_GLOVES = 10
    IE_WEAPON_ALT_RIGHT = 11
    IE_WEAPON_ALT_LEFT = 12


class Item:
    """Specialized class for managing the entirety of blocks concerned with items.
    This class serves two purposes. It may act as an actual item with properties attached to one item.
    Lists of such Items may be built. And it may serve as a monolithic analysis class for reading data
    from the master self.data bytes array."""
    def __init__(self,
                 data: bytes,
                 index_start: Optional[int] = None,
                 index_end: Optional[int] = None,
                 item_block: E_ItemBlock = E_ItemBlock.IB_UNSPECIFIED,
                 index_item_block: Optional[int] = None):
        """Initialization of the item.
        :param data: Binary block describing the entirety of a .d2s file.
        :param index_start
        :param index_end
        :param item_block: Item block this item is part of.
        :param index_item_block: Index of the item within the given block. I.e. the occurrence index of the item.
        [Note: This class does little sanity checks.]"""
        self.data = data
        self.index_start = index_start
        self.index_end = index_end
        self.item_block = item_block
        self.index_item_block = index_item_block

    @property
    def data_item(self) -> Optional[bytes]:
        if self.index_start is None or self.index_end is None:
            return None
        else:
            return self.data[self.index_start:self.index_end]

    @property
    def item_parent(self) -> Optional[E_ItemParent]:
        """Simple items Version 96: Bits 58-60"""
        data_item = self.data_item
        if (not data_item) or (len(data_item) < 8):
            return None
        # From 56,..,63 Bits 58-60
        val = (data_item[7] >> 2) & 7
        if val == 0:
            return E_ItemParent.IP_STORED
        elif val == 1:
            return E_ItemParent.IP_EQUIPPED
        elif val == 2:
            return E_ItemParent.IP_BELT
        elif val == 4:
            return E_ItemParent.IP_CURSOR
        elif val == 6:
            return E_ItemParent.IP_ITEM
        else:
            _log.warning(f"Encountered weird parent code {val}.")
            return E_ItemParent.IP_UNSPECIFIED

    @property
    def item_equipped(self) -> Optional[E_ItemEquipment]:
        """61-64"""
        data_item = self.data_item
        if (not data_item) or (len(data_item) < 9):
            return None
        # From 56-63 Bits 61-63 and bit 64.
        val = (data_item[7] >> 5) & 7
        val += data_item[8] & 1
        if val == 1:
            return E_ItemEquipment.IE_HELMET
        elif val == 2:
            return E_ItemEquipment.IE_AMULET
        elif val == 3:
            return E_ItemEquipment.IE_ARMOR
        elif val == 4:
            return E_ItemEquipment.IE_WEAPON_RIGHT
        elif val == 5:
            return E_ItemEquipment.IE_WEAPON_LEFT
        elif val == 6:
            return E_ItemEquipment.IE_RING_RIGHT
        elif val == 7:
            return E_ItemEquipment.IE_RING_LEFT
        elif val == 8:
            return E_ItemEquipment.IE_BELT
        elif val == 9:
            return E_ItemEquipment.IE_BOOTS
        elif val == 10:
            return E_ItemEquipment.IE_GLOVES
        elif val == 11:
            return E_ItemEquipment.IE_WEAPON_ALT_RIGHT
        elif val == 12:
            return E_ItemEquipment.IE_WEAPON_ALT_LEFT
        else:
            _log.warning(f"Encountered weird equipment code {val}.")
            return E_ItemEquipment.IE_UNSPECIFIED

    @property
    def item_stored(self) -> Optional[E_ItemStorage]:
        data_item = self.data_item
        if (not data_item) or (len(data_item) < 10):
            return None
        # 73-75
        # Bits 72-79 reduced to bits 73-75
        val = (data_item[9] >> 1) & 7
        if val == 1:
            return E_ItemStorage.IS_INVENTORY
        elif val == 4:
            return E_ItemStorage.IS_CUBE
        elif val == 5:
            return E_ItemStorage.IS_STASH
        else:
            _log.warning(f"Encountered weird storage code {val}.")
            return  E_ItemStorage.IS_UNSPECIFIED

    def get_block_index(self) -> Dict[E_ItemBlock, Tuple[int, int]]:
        """:param block: Target block.
        :returns index_start, index_end for the blocks in self.data. The index_end indices actually point
          to the first element of the next block (or are len(self.data) if eof is reached)."""
        n = len(self.data)
        res = dict()  # type: Dict[E_ItemBlock, Tuple[int, int]]

        # > Iterate through the diverse item blocks in sequence. -----
        # Player Header: Has only 4 bytes.
        index_start = self.data.find(b'JM')
        index_end = index_start + 4
        res[E_ItemBlock.IB_PLAYER_HD] = index_start, index_end

        # Player Items, Corpse Hd: Player item list is ended by the mandatory Corpse HD, which has 4 bytes.
        while True:
            index_start = self.data.find(b'JM', index_end)
            if index_start == -1:
                return res
            index_end = self.data.find(b'JM', index_start + 1)
            if index_end == -1:
                index_end = n
            if index_start - index_end == 4:
                res[E_ItemBlock.IB_PLAYER] = res[E_ItemBlock.IB_PLAYER_HD][1], index_start
                res[E_ItemBlock.IB_CORPSE_HD] = index_start, index_end
                break

        # Corpse Items, Mercenary Hd. index_end still points at the end of Corpse Header == start of Corpse Items.
        index_start_mercenary_hd = self.data.find(b'jf', index_end)
        if index_start_mercenary_hd >= 0:
            res[E_ItemBlock.IB_CORPSE] = index_end, index_start_mercenary_hd
            res[E_ItemBlock.IB_MERCENARY_HD] = index_start_mercenary_hd, index_start_mercenary_hd + 2
            index_start = res[E_ItemBlock.IB_MERCENARY_HD][1]
        else:
            res[E_ItemBlock.IB_CORPSE] = index_end, n
            return res

        # Mercenary Items, Iron Golem Header.
        index_start_golem_hd = self.data.find(b'kf', index_start)
        if index_start_golem_hd >= 0:
            res[E_ItemBlock.IB_MERCENARY] = index_start, index_start_golem_hd
            res[E_ItemBlock.IB_IRONGOLEM_HD] = index_start_golem_hd, index_start_golem_hd + 3
            index_start = res[E_ItemBlock.IB_IRONGOLEM_HD][1]
        else:
            res[E_ItemBlock.IB_MERCENARY] = index_start, n
            return res

        # Iron Golem Item. The remainder of the file.
        res[E_ItemBlock.IB_IRONGOLEM] = index_start, n
        # < ----------------------------------------------------------
        return res

    def get_block_item_index(self) -> Dict[E_ItemBlock, List[Tuple[int, int]]]:
        """:returns for each block a list of index-2-tuples for self.data.
        Each 3 tuple. Entries 0 and 1 index one item, thus that data[indexs_start:index_end] encompasses the entire
        item. The third entry is a copy of that binary blob."""
        block_index = self.get_block_index()
        keys_relevant = [E_ItemBlock.IB_PLAYER, E_ItemBlock.IB_CORPSE, E_ItemBlock.IB_MERCENARY, E_ItemBlock.IB_IRONGOLEM]
        res = dict()  # type: Dict[E_ItemBlock, List[Tuple[int, int]]]
        for key in block_index:
            if key not in keys_relevant:
                continue
            index_start_block, index_end_block = block_index[key]
            index_start = index_start_block
            item_end_item = index_start
            res[key] = list()
            while index_start >= 0:
                item_start = self.data[0:index_end_block].find(b'JM', index_start_block)
                if index_start < 0:
                    break
                index_end = self.data[0:index_end_block].find(b'JM', item_start + 1)
                if index_end < 0:
                    res[key].append((index_start, index_end_block))
                    break
                else:
                    res[key].append((index_start, index_end))
        return res

    def get_block_items(self, *, block: E_ItemBlock = E_ItemBlock.IB_UNSPECIFIED,
                          parent: E_ItemParent = E_ItemParent.IP_UNSPECIFIED,
                          equipped: E_ItemEquipment = E_ItemEquipment.IE_UNSPECIFIED,
                          stored: E_ItemStorage = E_ItemStorage.IS_UNSPECIFIED) -> List[Item]:
        """Get a list of items that matches all given filters. If everything is unspecified, all items are returned.
        :returns a List of tuples. Entries:
          * Start index within the master data structure.
          * End index (one point beyond the end) within the master data structure (or len(data) if it goes to EOF).
          * The bytes data of length (index_end - index_start) that is described by both indices."""
        index = self.get_block_item_index()  # type: Dict[E_ItemBlock, List[Tuple[int, int]]]
        blocks_relevant = [E_ItemBlock.IB_PLAYER, E_ItemBlock.IB_CORPSE, E_ItemBlock.IB_MERCENARY, E_ItemBlock.IB_IRONGOLEM] if block == E_ItemBlock.IB_UNSPECIFIED else [block]
        res = list()  # type: List[Item]
        for block_relevant in blocks_relevant:
            if block_relevant not in index:
                continue
            lst = index[block_relevant]
            for j in range(len(lst)):
                item = Item(self.data, lst[j][0], lst[j][1], block_relevant, j)
                if (parent in [E_ItemParent.IP_UNSPECIFIED, item.item_parent]) or \
                   (equipped in [E_ItemEquipment.IE_UNSPECIFIED, item.item_equipped]) or \
                   (stored in [E_ItemStorage.IS_UNSPECIFIED, item.item_stored]):
                    res.append(item)
        return res

    def __str__(self) -> str:
        data_item = self.data_item
        if data_item:
            return f"Item {self.item_block.name} #{self.index_item_block} index: ({self.index_start}, {self.index_end}): " \
                f"Parent: {self.item_parent.name}, Storage: {self.item_stored.name}, Equip: {self.item_equipped.name}"
        else:
            return "Analytic Item instance."


class Data:
    """Data object concerned with the binary content of the entirety of a .d2s save game file."""
    def __init__(self, data: Union[bytes, str]):
        """:param data: Either a string holding a .d2s file name, or a binary data blob of an already read such file."""
        if isinstance(data, str):
            with open(data, 'rb') as IN:
                self.data = IN.read()
            self.pfname = data
        elif isinstance(data, bytes):
            self.data = data
            self.pfname = self.get_name(True) + '.d2s'
        else:
            raise ValueError(f"Given parameter data is of unusable type '{type(data).__name__}'.")

    def checksum_compute(self) -> bytes:
        csum = 0
        for j in range(len(self.data)):
            elt = 0 if 12 <= j < 16 else self.data[j]
            csum = ((csum << 1) + elt) % 0xffffffff
        csum = csum.to_bytes(4, 'little')
        return csum

    def checksum_update(self) -> bytes:
        """Important function! Will update the checksum entry. This is important to be done as final
        step before saving. If the checksum does not reflect the save game file, the game will not accept it.
        :returns the checksum in a 4-byte binary string. Also updates the self.data accordingly."""
        csum = self.checksum_compute()
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

    def is_hardcore(self) -> bool:
        """The bit of index 2 in status byte 36  decides if a character is hardcore."""
        return self.data[36] & 4 > 0

    def is_dead(self) -> bool:
        """The bit of index 3 in status byte 36 decides if a character is dead."""
        return self.data[36] & 8 > 0

    def set_hardcore(self, to_hardcore: bool):
        """Sets the character to hardcore or non-hardcore.
        :param to_hardcore: Setting to hardcore if and only if this is True. Else to Softcore."""
        val = self.data[36]
        if to_hardcore:
            val |= 4
        else:
            val &= 251
        self.data[0:36] + val.to_bytes(1, 'little') + self.data[37:]

    #def get_items(self) -> Dict[E_ItemSites]:
    #    pass

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """":return Time string aiming to become part of a backup pfname."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def save2disk(self, pfname: str, prefix_timestamp: bool = False):
        """Write this data structure's current state to disk. As is. E.g., no checksums are updated automatically."""
        if prefix_timestamp:
            parts = os.path.split(pfname)
            pname = parts[0]
            fname = parts[1]
            pfname = os.path.join(pname, Data.get_time() + '_' + fname + '.backup')
        with open(pfname, 'wb') as OUT:
            OUT.write(self.data)
        print(f"Wrote {self.get_class(True)} {self.get_name(True)} to disk: {pfname}")

    def __str__(self) -> str:
        msg = f"{self.get_name(True)}, a level {self.data[43]} {self.get_class(True)}. "\
              f"Checksum (current): '{int.from_bytes(self.get_checksum(), 'little')}', "\
              f"Checksum (computed): '{int.from_bytes(self.checksum_compute(), 'little')}, "\
              f"file size: {len(self.data)}"
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
        # Corpse and https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#items
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
        desc = """Tool script for doing small scale changes to Diablo II .d2s save game files.

Motivating example is the --exchange function. Have two characters stuff items into their Horadric cubes.
Apply this script to both their .d2s files, using the --exchange flag. Then this script will attempt to alter
both files thus, that the Horadric Cube contents of both players switch places."""
        epilog = f"""Example call:
$ python3 {Path(sys.argv[0]).name} conan.d2s ormaline.d2s"""
        parser = argparse.ArgumentParser(prog='Horadric Exchange', description=desc, epilog=epilog, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--omit_backup', action='store_true',
            help="Per default, target files will be backupped to .backup files. For safety. This option will disable that safety.")
        parser.add_argument('--exchange', action='store_true', help="Flag. Requires that there are precisely 2 character pfnames given. This will exchange their Horadric Cube contents.")
        parser.add_argument('--save_horadric', type=str, help="Write the items found in the Horadric Cube to disk.")
        parser.add_argument('--load_horadric', type=str, help="Drop all contents from the Horadric Cube and replace them with the horadric file content, that had been written using --save_horadric earlier.")
        parser.add_argument('--hardcore', action='store_true', help="Flag. Set target characters to hard core mode.")
        parser.add_argument('--softcore', action='store_true', help="Flag. Set target characters to soft core mode.")
        parser.add_argument('--info', action='store_true', help="Flag. Show some statistics to each input file.")
        parser.add_argument('pfnames', nargs='+', type=str, help='List of path and filenames to target .d2s character files.')
        parsed = parser.parse_args(sys.argv[1:])  # type: argparse.Namespace
        return parsed

if __name__ == '__main__':
    hor = Horadric()
    print("Done.")

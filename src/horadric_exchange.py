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
import pathlib
import re
import sys
import time
import logging
import argparse
from argparse import RawTextHelpFormatter
# from idlelib.stackviewer import VariablesTreeItem
from math import floor, ceil
from pathlib import Path
from copy import deepcopy
from platform import android_ver
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


def reverse_bit_order(val: int, width: int):
    """Some values are in bit reverse order. Guess, the powers that be at Blizzard North did that on purpose.
    :param val: Value to reverse.
    :param width: Width of the value to reverse in bits.
        About bit lengths of attributes: https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#attribute-bit-lengths
    :return: Reversed value."""
    return int('{:0{width}b}'.format(val, width=width)[::-1], 2)


def read_bitfield(data: bytes, bit0: int = 0, n_bits: Optional[int] = None, *, reverse = False) -> int:
    """Free function for reading or writing a bit field value.
    :param data: some bytes block.
    :param bit0: First bit index to read. 0-starting index, of course.
    :param n_bits: Number of bits to be read.
    :param reverse: Should the bit order of the result be reversed prior to returning?
    :returns the unsigned int value associated with the given bit-set. Or 0 in case of failure."""
    if n_bits is None:
        n_bits = len(data) * 8
    res = 0  # type: int
    n = len(data)
    offset_byte_left = int(floor(bit0) / 8)
    n_bytes = int(ceil(n_bits / 8))
    offset_bit_left = bit0 % 8
    sb_raw = int.from_bytes(data[offset_byte_left:(offset_byte_left + n_bytes)], 'little')
    b0 = '{:0{width}b}'.format(sb_raw, width=n_bytes*8)
    b1 = b0[offset_bit_left:(offset_bit_left + n_bits)]
    res = int(b1, 2)
    if reverse:
        res = reverse_bit_order(res, n_bits)
    return res


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
    def is_analytical(self) -> bool:
        return self.index_start is None or self.index_end is None

    @property
    def data_item(self) -> Optional[bytes]:
        if self.is_analytical:
            return None
        else:
            return self.data[self.index_start:self.index_end]

    @property
    def item_parent(self) -> Optional[E_ItemParent]:
        """Simple items Version 96: Bits 58-60"""
        if self.is_analytical:
            return None
        data_item = self.data_item
        if len(data_item) < 8:
            return E_ItemParent.IP_UNSPECIFIED
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
        if self.is_analytical:
            return None
        data_item = self.data_item
        if len(data_item) < 9:
            return E_ItemEquipment.IE_UNSPECIFIED
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
            if val != 0:
                _log.warning(f"Encountered weird equipment code {val}.")
            return E_ItemEquipment.IE_UNSPECIFIED

    @property
    def item_stored(self) -> Optional[E_ItemStorage]:
        if self.is_analytical:
            return None
        data_item = self.data_item
        if len(data_item) < 10:
            return E_ItemStorage.IS_UNSPECIFIED
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
            if val != 0:
                _log.warning(f"Encountered weird storage code {val}.")
            return  E_ItemStorage.IS_UNSPECIFIED

    @staticmethod
    def drop_empty_block_indices(block_indices: Dict[E_ItemBlock, Tuple[int, int]]) -> Dict[E_ItemBlock, Tuple[int, int]]:
        # Drop empty blocks.
        deletees = list()  # type: List[E_ItemBlock]
        for key in block_indices:
            if block_indices[key][0] == block_indices[key][1]:
                deletees.append(key)
        for key in deletees:
            del block_indices[key]
        return block_indices

    def get_block_index(self) -> Dict[E_ItemBlock, Tuple[int, int]]:
        """:returns index_start, index_end for the blocks in self.data. The index_end indices actually point
          to the first element of the next block (or are len(self.data) if eof is reached)."""
        n = len(self.data)
        res = dict()  # type: Dict[E_ItemBlock, Tuple[int, int]]

        # > Iterate through the diverse item blocks in sequence. -----
        # Player Header: Has only 4 bytes. Main file header is of 765 bytes length.
        index_start = self.data.find(b'JM', 765)
        index_end = index_start + 4
        res[E_ItemBlock.IB_PLAYER_HD] = index_start, index_end

        # Player Items, Corpse Hd: Player item list is ended by the mandatory Corpse HD, which starts 'JM' and has 16 bytes.
        index_start_player = index_end
        while True:
            index_start = self.data.find(b'JM', index_end)
            if index_start == -1:
                return Item.drop_empty_block_indices(res)
            index_end = self.data.find(b'JM', index_start + 1)
            if (index_end == -1) or ((index_end - index_start) == 16) or (self.data[(index_end-2):index_end] in [b'jf', b'kf']):
                # We have found the corpse header.
                delta_corpse_hd = 16 if ((index_end - index_start) == 16) else 4
                res[E_ItemBlock.IB_CORPSE_HD] = index_start, (index_start + delta_corpse_hd)
                break
            else:
                res[E_ItemBlock.IB_PLAYER] = index_start_player, index_end

        # Corpse Items, Mercenary Header. Mercenary Hd begins 'jf' followed by 'JM' and a 2-byte item count.
        index_end = res[E_ItemBlock.IB_CORPSE_HD][1]
        index_start_mercenary_hd = self.data.find(b'jf', index_end)
        index_start_golem_hd = self.data.find(b'kf', index_end)
        index_end_corpse = index_start_mercenary_hd if index_start_mercenary_hd >= 0 else index_start_golem_hd
        if index_end_corpse < 0:
            index_end_corpse = n
        if res[E_ItemBlock.IB_CORPSE_HD][1] != index_end_corpse:
            res[E_ItemBlock.IB_CORPSE] = res[E_ItemBlock.IB_CORPSE_HD][1], index_end_corpse

        if index_start_mercenary_hd >= 0:
            # Mercenary Header: "jfJM<2 byte-direct item count>"
            mercenary_hd_is_large = (self.data.find(b'JM', index_start_mercenary_hd) == (index_start_mercenary_hd + 2)) and \
                                    (self.data.find(b'JM', index_start_mercenary_hd + 3) == (index_start_mercenary_hd + 6))
            res[E_ItemBlock.IB_MERCENARY_HD] = index_start_mercenary_hd, (index_start_mercenary_hd + (6 if mercenary_hd_is_large else 2))
            index_start = res[E_ItemBlock.IB_MERCENARY_HD][1]
        else:
            return Item.drop_empty_block_indices(res)

        # Mercenary Items, Iron Golem Header.
        index_start_golem_hd = self.data.find(b'kf', index_start)
        if index_start_golem_hd >= 0:
            res[E_ItemBlock.IB_MERCENARY] = index_start, index_start_golem_hd
            res[E_ItemBlock.IB_IRONGOLEM_HD] = index_start_golem_hd, index_start_golem_hd + 3
            index_start = res[E_ItemBlock.IB_IRONGOLEM_HD][1]
        else:
            res[E_ItemBlock.IB_MERCENARY] = index_start, n
            return Item.drop_empty_block_indices(res)

        # Iron Golem Item. The remainder of the file.
        res[E_ItemBlock.IB_IRONGOLEM] = index_start, n
        # < ----------------------------------------------------------
        return Item.drop_empty_block_indices(res)

    def get_block_item_index(self) -> Dict[E_ItemBlock, List[Tuple[int, int]]]:
        """:returns for each block a list of index-2-tuples for self.data.
        Each 3 tuple. Entries 0 and 1 index one item, thus that data[indexs_start:index_end] encompasses the entire
        item. The third entry is a copy of that binary blob."""
        block_index = self.get_block_index()
        res = dict()  # type: Dict[E_ItemBlock, List[Tuple[int, int]]]
        for key in block_index:
            index_start_block, index_end_block = block_index[key]
            index_start = index_start_block
            res[key] = list()
            while index_start >= 0:
                index_start = self.data[0:index_end_block].find(b'JM', index_start)
                if index_start < 0:
                    if not res[key]:
                        res[key].append((index_start_block, index_end_block))
                    break
                index_end = self.data[0:index_end_block].find(b'JM', index_start + 1)
                if index_end < 0:
                    res[key].append((index_start, index_end_block))
                    break
                else:
                    res[key].append((index_start, index_end))
                    index_start = index_end
        return res

    def get_block_items(self, block: E_ItemBlock = E_ItemBlock.IB_UNSPECIFIED,
                          parent: E_ItemParent = E_ItemParent.IP_UNSPECIFIED,
                          equipped: E_ItemEquipment = E_ItemEquipment.IE_UNSPECIFIED,
                          stored: E_ItemStorage = E_ItemStorage.IS_UNSPECIFIED) -> List[Item]:
        """Get a list of items that matches all given filters. If everything is unspecified, all items are returned.
        :returns a List of tuples. Entries:
          * Start index within the master data structure.
          * End index (one point beyond the end) within the master data structure (or len(data) if it goes to EOF).
          * The bytes data of length (index_end - index_start) that is described by both indices."""
        index = self.get_block_item_index()  # type: Dict[E_ItemBlock, List[Tuple[int, int]]]
        res = list()  # type: List[Item]
        for block_relevant in index:
            if (block != E_ItemBlock.IB_UNSPECIFIED) and block_relevant != block:
                continue
            lst = index[block_relevant]
            for j in range(len(lst)):
                item = Item(self.data, lst[j][0], lst[j][1], block_relevant, j)
                if (parent in [E_ItemParent.IP_UNSPECIFIED, item.item_parent]) or \
                   (equipped in [E_ItemEquipment.IE_UNSPECIFIED, item.item_equipped]) or \
                   (stored in [E_ItemStorage.IS_UNSPECIFIED, item.item_stored]):
                    res.append(item)
        return res

    def get_cube_contents(self) -> List[Item]:
        """:returns list of items and socketed items found in the Horadric Cube."""
        items = self.get_block_items(E_ItemBlock.IB_PLAYER)
        found_cube = False
        res = list()  # type: List[Item]
        for item in items:
            if item.item_stored == E_ItemStorage.IS_CUBE:
                found_cube = True
            if not found_cube:
                continue
            if item.item_stored == E_ItemStorage.IS_CUBE or item.item_parent == E_ItemParent.IP_ITEM:
                res.append(item)
            else:
                break
        return res

    def __str__(self) -> str:
        if self.is_analytical:
            return "Analytic Item instance."
        else:
            return f"Item {self.item_block.name} #{self.index_item_block} index: ({self.index_start}, {self.index_end}): " \
                f"Parent: {self.item_parent.name}, Storage: {self.item_stored.name}, Equip: {self.item_equipped.name}"


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

    def compute_checksum(self) -> bytes:
        """:returns a newly computed checksum for self.data."""
        csum = 0
        for j in range(len(self.data)):
            elt = 0 if 12 <= j < 16 else self.data[j]
            csum = ((csum << 1) + elt) % 0xffffffff
        csum = csum.to_bytes(4, 'little')
        return csum

    def update_checksum(self) -> bytes:
        """Important function! Will update the checksum entry. This is important to be done as final
        step before saving. If the checksum does not reflect the save game file, the game will not accept it.
        :returns the checksum in a 4-byte binary string. Also updates the self.data accordingly."""
        csum = self.compute_checksum()
        self.data = self.data[0:12] + csum + self.data[16:]
        print("Updated checksum.")
        return csum

    def get_checksum(self) -> bytes:
        """:returns the checksum as it is written within the current self.data byte block."""
        return self.data[12:16]

    def update_file_size(self) -> int:
        """Updates this self.data block with the correct file-size.
        :returns the actual size of self.data in bytes."""
        n = len(self.data)
        sz = n.to_bytes(4, 'little')
        self.data = self.data[0:8] + sz + self.data[12:]
        return n

    def update_all(self):
        """Convenience shortcut doing all updates that are necessary prior to writing a valid file to disk."""
        self.update_file_size()
        self.update_checksum()

    def get_file_size(self) -> int:
        """:returns the file size as it is written within self.data."""
        return int.from_bytes(self.data[8:12], 'little')

    def get_item_count_mercenary(self, as_int = False) -> Union[int, bytes]:
        index_hd = self.data.find(b'jfJM', 765)
        if index_hd < 0:
            return 0 if as_int else b'\x00\x00'
        else:
            val = self.data[(index_hd + 4):(index_hd + 5)]
            if not as_int:
                return val
            else:
                return int.from_bytes(val, 'little')

    def get_item_count_player(self, as_int = False) -> Union[int, bytes]:
        """TODO! Improve code redundancy to get_item_count_mercenary(..)"""
        index_hd = self.data.find(b'JM', 765)
        if index_hd < 0:
            return 0 if as_int else b'\x00\x00'
        else:
            val = self.data[(index_hd + 2):(index_hd + 3)]
            if not as_int:
                return val
            else:
                return int.from_bytes(val, 'little')

    def set_item_count(self, block: E_ItemBlock, val: int):
        if block == E_ItemBlock.IB_PLAYER_HD:
            index_begin = self.data.find(b'JM', 765) + 2
            index_end = index_begin + 2
            self.data = self.data[0:index_begin] + int.to_bytes(val, 2, 'little') + self.data[index_end:]
        else:
            _log.warning(f"Failure to set item count for hitherto unsupported block '{block.name}'.")

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
        self.data = self.data[0:36] + val.to_bytes(1, 'little') + self.data[37:]
        print(f"Set {self.get_name(True)} to {'hard' if to_hardcore else 'soft'}core.")

    def drop_item(self, item: Item) -> int:
        """Removes target item from this data object. Does no deeper checks and does no updates of stuff like the checksum."""
        index_start = item.index_start
        index_end = item.index_end
        if index_start >= index_end:
            _log.warning(f"Will refrain from dropping weird item '{item}'.")
        else:
            if item.item_parent != E_ItemParent.IP_ITEM:
                if item.item_block == E_ItemBlock.IB_PLAYER:
                    self.set_item_count(E_ItemBlock.IB_PLAYER_HD, self.get_item_count_player(True) - 1)
                elif item.item_block == E_ItemBlock.IB_MERCENARY:
                    self.set_item_count(E_ItemBlock.IB_MERCENARY_HD, self.get_item_count_mercenary(True) - 1)
                else:
                    _log.warning(f"Unsupported drop target block: {item.item_block.name}. Doing nothing.")
                    return 1
            self.data = self.data[0:index_start] + self.data[index_end:]
        return 0

    def add_items_to_player(self, items: bytes) -> int:
        """Warning: Be sure to add multiple items in a sensible order!"""
        index_start = Item(self.data).get_block_index()[E_ItemBlock.IB_PLAYER][0]
        self.data = self.data[0:index_start] + items[1:] + self.data[index_start:]
        count = int.from_bytes(items[0:1], 'little')
        self.set_item_count(E_ItemBlock.IB_PLAYER_HD, self.get_item_count_player(True) + count)
        print(f"Attempting to add {count} new items to the player's inventory.")
        return 0

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """":return Time string aiming to become part of a backup pfname."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def save2disk(self, pfname: str = None, prefix_timestamp: bool = False):
        """Write this data structure's current state to disk. As is. E.g., no checksums are updated automatically."""
        if pfname is None:
            pfname = self.pfname
        if prefix_timestamp:
            parts = os.path.split(pfname)
            pname = parts[0]
            fname = parts[1]
            pfname = os.path.join(pname, Data.get_time() + '_' + fname + '.backup')
        with open(pfname, 'wb') as OUT:
            OUT.write(self.data)
        print(f"Wrote {self.get_class(True)} {self.get_name(True)} to disk: {pfname}")

    def __str__(self) -> str:
        core = 'hardcore' if self.is_hardcore() else 'softcore'
        msg = f"{self.get_name(True)}, a level {self.data[43]} {core} {self.get_class(True)}. "\
              f"Checksum (current): '{int.from_bytes(self.get_checksum(), 'little')}', "\
              f"Checksum (computed): '{int.from_bytes(self.compute_checksum(), 'little')}, "\
              f"file size: {len(self.data)}, file size in file: {self.get_file_size()}, \n" \
              f"direct player item count: {self.get_item_count_player(True)}, is dead: {self.is_dead()}, direct mercenary item count: {self.get_item_count_mercenary(True)}"
        item_analysis = Item(self.data)
        for item in item_analysis.get_block_items():
            msg += f"\n{item}"
        return msg


class Horadric:
    def __init__(self, args: Optional[List[str]] = None):
        # > Setting up the data. -------------------------------------
        parsed = self.parse_arguments(args)
        pfnames_in = parsed.pfnames  # type: List[str]
        self.data_all = [Data(pfname) for pfname in pfnames_in]
        #< -----------------------------------------------------------
        #> Backups. --------------------------------------------------
        do_backup = not parsed.omit_backup  # type: bool
        if do_backup:
            self.backup()
        else:
            print("Omitting backups.")
        # < ----------------------------------------------------------
        if parsed.info:
            self.print_info()

        if parsed.softcore and parsed.hardcore:
            print("Both, set to hardcore and set to softcore has been requested. Ignoring both.")
        elif parsed.softcore or parsed.hardcore:
            self.set_hardcore(parsed.hardcore)

        if parsed.drop_horadric:
            for data in self.data_all:
                self.drop_horadric(data)

        if parsed.save_horadric:
            if len(pfnames_in) == 1:
                self.save_horadric(parsed.save_horadric)
            else:
                _log.warning("Saving of Horadric Cube content requires 1 target character exactly.")

        if parsed.load_horadric:
            if len(pfnames_in) == 1:
                self.load_horadric(parsed.load_horadric)
            else:
                _log.warning("Loading of Horadric Cube content requires 1 target character exactly.")

        if parsed.exchange_horadric:
            if len(pfnames_in) == 2:
                self.exchange_horadric()
            else:
                _log.warning("Exchanging Horadric Cube contents requires 2 target characters exactly.")

    def backup(self):
        _log.warning("Backups deactivated during active development. TODO: Do backups!")

    def print_info(self):
        """Print various info to all files to the console."""
        n = len(self.data_all)
        for j in range(n):
            print(self.data_all[j])
            if j < (n-1):
                print("====================")

    def set_hardcore(self, hardcore: bool):
        for data in self.data_all:
            data.set_hardcore(hardcore)
            data.update_all()
            data.save2disk()

    def drop_horadric(self, data: Data):
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        # [Note: Iterate in reversed order, so that dropping front items will not destroy indices for back items.]
        for item in reversed(items):
            data.drop_item(item)
        data.update_all()
        data.save2disk()
        print(f"Dropped {len(items)} items from the Horadric cube.")

    @staticmethod
    def grep_horadric(data: Data) -> bytes:
        """:returns a one-byte prefix with the number of counting items and then the
        block of item byte code."""
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        res = b''
        count = 0
        for item in items:
            res += item.data_item
            if item.item_parent != E_ItemParent.IP_ITEM:
                count = count + 1
        print(f"Grepped {len(items)} items ({count} counting).")
        return count.to_bytes(1, 'little') + res

    def save_horadric(self, pfname_out: str):
        """Writes the horadric cube raw contents to disk. Employs that these contents are in order.
        Target file structure: Number of main items, bytes block of all cube items."""
        data = self.data_all[0]
        res = self.grep_horadric(data)
        with open(pfname_out, 'wb') as OUT:
            OUT.write(res)
        print(f"Wrote file '{pfname_out}'.")

    def insert_horadric(self, data: Data, items: bytes):
        """Takes a byte block of Horadric cube player items and moves it into the players Horadric Cube.
        Replaces old contents.
        After this is done the character file is saved automatically."""
        self.drop_horadric(data)
        if not data.add_items_to_player(items):
            data.update_all()
            data.save2disk()

    def load_horadric(self, pfname_in) -> int:
        if len(self.data_all) != 1:
            _log.warning(f"Horadric cube content loading requires one target character exactly.")
            return 1
        if not os.path.isfile(pfname_in):
            _log.warning(f"File '{pfname_in}' could not be opened for reading,")
            return 2
        with open(pfname_in, 'rb') as IN:
            code = IN.read()
        data = self.data_all[0]
        self.insert_horadric(data, code)
        return 0

    def exchange_horadric(self) -> int:
        if not len(self.data_all) == 2:
            _log.warning("The Horadric Exchange requires two Character files precisely!")
            return 1
        horadric0 = self.grep_horadric(self.data_all[0])
        horadric1 = self.grep_horadric(self.data_all[1])
        self.insert_horadric(self.data_all[0], horadric1)
        self.insert_horadric(self.data_all[1], horadric0)
        print("Horadric exchange complete.")
        return 0

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
        parser.add_argument('--exchange_horadric', action='store_true', help="Flag. Requires that there are precisely 2 character pfnames given. This will exchange their Horadric Cube contents.")
        parser.add_argument('--drop_horadric', action='store_true', help="Flag. If given, the Horardric Cube contents of the targetted character will be removed.")
        parser.add_argument('--save_horadric', type=str, help="Write the items found in the Horadric Cube to disk with the given pfname. Only one character allowed.")
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

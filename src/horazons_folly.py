#!/usr/bin/python3
"""
Python script for exchanging the Horadric Cube contents of two Diablo II characters. Chiefly aiming at legacy v1.12.

Literature:
===========
[1] https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md
  Description of the Diablo 2 save game format. Quite good. Principal source of information.
[1b] https://user.xmission.com/~trevin/DiabloIIv1.09_Mercenaries.html
  Mercenary info decoded.
[2] https://d2mods.info/forum/viewtopic.php?t=9011
  Another comprehensive file format analysis is hidden within this thread. It differs from [1]
  For instance: Item bit index [150:154] is quality and [143:150] ist der item level.
[3] https://www.gmstemple.com/Diablo2/itemcodes.html
  Large list of 3-letter item codes. E.g., the item codes for the runes are 'r01'-'r33'
[4] Python >=3.6 seems to guarantee key order in dicts.
  https://discuss.codecademy.com/t/does-the-dictionary-keys-function-return-the-keys-in-any-specific-order/354717

Fun facts:
v1.12, which is the one I am interested in has version code "96". More precisely, "96" is for "v1.10 - v1.14d"

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/01/29.
"""

from __future__ import annotations

import re
import os
import sys
import time
import logging
import argparse
from os.path import expanduser
from collections import OrderedDict as odict
from argparse import RawTextHelpFormatter
from pathlib import Path
from math import ceil, floor
from typing import List, Dict, Optional, Union, Tuple, OrderedDict, Any
from enum import Enum


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

regexp_invalid_pfname_chars = r'[/\\?%*:|"<> !]'


class E_ItemClass(Enum):
    IC_OTHER = 0
    IC_HELM = 1
    IC_BODY_ARMOR = 2
    IC_SHIELDS = 3
    IC_GLOVES = 4
    IC_BOOTS = 5
    IC_BELTS = 6
    IC_DRUID_PELTS = 7
    IC_BARBARIAN_HELMS = 8
    IC_PALADIN_SHIELDS = 9
    IC_SHRUNKEN_HEADS = 10
    IC_CIRCLETS = 11
    IC_AXES = 12
    IC_MACES = 13
    IC_SWORDS = 14
    IC_DAGGERS = 15
    IC_THROWING = 16
    IC_JAVELINS = 17
    IC_THROWING_POTIONS = 18
    IC_SPEARS = 19
    IC_POLEARMS = 20
    IC_BOWS = 21
    IC_CROSSBOWS = 22
    IC_STAVES = 23
    IC_WANDS = 24
    IC_SCEPTERS = 25
    IC_ASSASSIN_KATARS = 26
    IC_SORCERESS_ORBS = 27
    IC_AMAZON_WEAPONS = 28
    IC_QUEST_ITEMS = 29
    IC_GEMS = 30
    IC_RUNES = 31
    IC_POTIONS = 32
    IC_CHARMS = 33
    IC_SCROLLS = 34
    IC_TOMES = 35
    IC_MISC = 36

    def volume_default(self) -> Tuple[int, int]:
        """:returns (rows,cols) an item of this class typically takes in inventory, preferring large sizes.
        This is not always correct. In these cases the file item_codes.tsv may hold a correction.
        See implementation of load_item_family_list(..) below for details."""
        if self in [E_ItemClass.IC_OTHER, E_ItemClass.IC_SCROLLS, E_ItemClass.IC_THROWING_POTIONS,
                    E_ItemClass.IC_POTIONS, E_ItemClass.IC_RUNES, E_ItemClass.IC_GEMS]:
            return 1, 1
        elif self == E_ItemClass.IC_BELTS:
            return 1, 2
        elif self in [E_ItemClass.IC_THROWING, E_ItemClass.IC_WANDS, E_ItemClass.IC_SORCERESS_ORBS, E_ItemClass.IC_TOMES]:
            return 2, 1
        elif self in [E_ItemClass.IC_HELM, E_ItemClass.IC_GLOVES, E_ItemClass.IC_BOOTS, E_ItemClass.IC_DRUID_PELTS,
                      E_ItemClass.IC_BARBARIAN_HELMS, E_ItemClass.IC_SHRUNKEN_HEADS, E_ItemClass.IC_CIRCLETS]:
            return 2, 2
        elif self in [E_ItemClass.IC_DAGGERS, E_ItemClass.IC_JAVELINS,
                      E_ItemClass.IC_ASSASSIN_KATARS, E_ItemClass.IC_CHARMS]:
            return 3, 1
        elif self in [E_ItemClass.IC_BODY_ARMOR, E_ItemClass.IC_SCEPTERS, E_ItemClass.IC_MISC]:
            return 3, 2
        elif self in [E_ItemClass.IC_SHIELDS, E_ItemClass.IC_PALADIN_SHIELDS, E_ItemClass.IC_AXES,
                      E_ItemClass.IC_MACES, E_ItemClass.IC_SWORDS, E_ItemClass.IC_SPEARS, E_ItemClass.IC_POLEARMS,
                      E_ItemClass.IC_BOWS, E_ItemClass.IC_CROSSBOWS, E_ItemClass.IC_STAVES,
                      E_ItemClass.IC_AMAZON_WEAPONS, E_ItemClass.IC_QUEST_ITEMS]:
            return 4, 2
        else:
            _log.warning(f"Unsupported ItemClass '{self}' encountered. Returning conservative (4,2).")
            return 4, 2

    @property
    def is_socketable(self) -> bool:
        return self in [E_ItemClass.IC_HELM, E_ItemClass.IC_BODY_ARMOR, E_ItemClass.IC_SHIELDS,
                        E_ItemClass.IC_PALADIN_SHIELDS, E_ItemClass.IC_DRUID_PELTS, E_ItemClass.IC_BARBARIAN_HELMS,
                        E_ItemClass.IC_SHRUNKEN_HEADS, E_ItemClass.IC_CIRCLETS, E_ItemClass.IC_AXES,
                        E_ItemClass.IC_MACES, E_ItemClass.IC_SWORDS, E_ItemClass.IC_DAGGERS,
                        E_ItemClass.IC_SPEARS, E_ItemClass.IC_POLEARMS, E_ItemClass.IC_BOWS, E_ItemClass.IC_CROSSBOWS,
                        E_ItemClass.IC_STAVES, E_ItemClass.IC_WANDS, E_ItemClass.IC_SCEPTERS,
                        E_ItemClass.IC_ASSASSIN_KATARS, E_ItemClass.IC_SORCERESS_ORBS, E_ItemClass.IC_AMAZON_WEAPONS]

    def __str__(self):
        return re.sub("^IC_", "", self.name).lower()

class E_ItemGrade(Enum):
    IG_NONE = 10  # type: int
    IG_NORMAL = 0  # type: int
    IG_EXCEPTIONAL = 1  # type: int
    IG_ELITE = 2  # type: int
    """Exclusively for circlets:"""
    IG_POSTELITE = 3    # type: int

    def __str__(self):
        return re.sub("^IG_", "", self.name).lower()

"""Based on [3]. Maps item type codes to actual items. Also gives insight in some meta-information on the topic."""
# [Note: This is a forward-declaration! https://medium.com/lets-learn-python/forward-declarations-in-python-cad6c736da6a ]
l_item_families: list  # type: List[ItemFamily]

class ItemFamily:
    def __init__(self, code_names: OrderedDict[str, str], item_class: E_ItemClass, *, rows: Optional[int]=None, cols: Optional[int]=None):
        """An ItemFamily is concerned with a row from the beautiful table [3].
        It associates the entries with each other and explains whether they are armor or weapon.
        :param code_names: Keys are item codes. E.g., cap, xap, or uap.
        Ordered by group: Normal first, then exceptional, elite, and, in the case of circlets,
          post-elite.
        Values are item names. In this example: Cap, War Hat and Shako.
        :param item_class: What is it at first glance? An axe? A shrunken head? Or what?
        :param rows: Number of rows this item should take. If not given will use hint from E_ItemClass entry."""
        self.code_names = code_names
        self.item_class = item_class
        try:
            self._rows = None if rows is None else int(rows)
            self._cols = None if cols is None else int(cols)
        except ValueError as err:
            _log.warning(f"Unparsable rows '{rows}' or cols '{cols}': {err}")

    @property
    def is_armor(self) -> bool:
        return 1 <= self.item_class.value <= 11

    @property
    def is_weapon(self) -> bool:
        if len(self.code_names) > 0 and any([key in self.code_names for key in ('leg', 'hdm', 'msf', 'hst', 'g33', 'qf1', 'qf2', 'hfh')]):
            return True
        return 12 <= self.item_class.value <= 28

    @property
    def is_stack(self) -> bool:
        return self.item_class in [E_ItemClass.IC_THROWING, E_ItemClass.IC_JAVELINS, E_ItemClass.IC_THROWING_POTIONS]

    @property
    def rows(self) -> int:
        """Number of rows this item takes up in inventory. At most. Accuracy depends on item_codes.tsv."""
        return self.item_class.volume_default()[0] if self._rows is None else self._rows

    @property
    def cols(self) -> int:
        """Number of cols this item takes up in inventory. At most. Accuracy depends on item_codes.tsv."""
        return self.item_class.volume_default()[1] if self._cols is None else self._cols

    def __str__(self):
        return f"{self.item_class} ({self.rows},{self.cols}): {self.code_names}"

    @staticmethod
    def get_family_by_code(code: str, data: Optional[List[ItemFamily]] = None) -> Optional[ItemFamily]:
        if not code:
            return None
        if not data:
            data = l_item_families
        for item_family in data:
            if code in item_family.code_names:
                return item_family
        return None

    @staticmethod
    def get_grade_for_code(code: str, data: Optional[List[ItemFamily]] = None) -> Optional[E_ItemGrade]:
        fam = ItemFamily.get_family_by_code(code, data)
        if not fam:
            return None
        c = 0
        for key in fam.code_names:
            if key == code:
                return E_ItemGrade(c)
            else:
                c = c + 1
        return None

    @staticmethod
    def get_sibling_code_for_grade(code: str, grade_target: E_ItemGrade, data: Optional[List[ItemFamily]] = None) -> Optional[str]:
        """Get the partner code for a given code from the same family that matches the given item grade.
        :param code: item 3 letter type_code.
        :param data: List of ItemFamilies. Will default to global l_item_families.
        :param grade_target: Target grade.
        :return None in case of failure. Else the 3-letter type code of the item within the same family as given code
          matching the given grade_target."""
        if not code:
            return None
        if not data:
            data = l_item_families
        it_fam = ItemFamily.get_family_by_code(code, data)
        if not it_fam:
            return None
        keys = list(it_fam.code_names.keys())
        return keys[grade_target.value] if grade_target.value < len(it_fam.code_names) else None

    @staticmethod
    def get_name_by_code(code: str, data: Optional[List[ItemFamily]] = None) -> Optional[str]:
        if not code:
            return None
        if not data:
            data = l_item_families
        it_fam = ItemFamily.get_family_by_code(code, data)
        if not it_fam:
            return None
        else:
            return it_fam.code_names[code]

    @staticmethod
    def load_item_family_list(pfname: Optional[str] = None) -> List[ItemFamily]:
        if not pfname:
            pfname = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'item_codes.tsv')
        if not os.path.isfile(pfname):
            _log.warning(f"Failure to open item code file '{pfname}' for reading. Continuing without item codes.")
            return list()
        res = list()  # type: List[ItemFamily]
        current_class = E_ItemClass.IC_OTHER
        with open(pfname, 'r') as IN:
            for line in IN:
                if re.findall("^\\s*#", line) or re.findall("^\\s*$", line):
                    continue  # << Ignore comment and empty lines.
                # Drop the trailing newline character.
                line = re.sub("\n$", "", line)
                try:
                    line, extension = re.split("\\s*;\\s*", line, maxsplit=1)
                except ValueError:
                    extension = ''
                line = re.split("\t", line)
                if len(line) == 1:
                    current_class = E_ItemClass['IC_' + line[0].upper()]
                    continue
                if len(line) % 2 > 0:
                    _log.warning(f"Ignoring strange item code line of odd entry number: '{line}'.")
                    continue
                od = odict()
                for j in range(round(len(line) / 2)):
                    od[line[2*j + 1]] = line[2*j]
                volume = re.findall("[0-9]+", extension)
                if len(volume) == 2:
                    res.append(ItemFamily(od, current_class, rows=volume[0], cols=volume[1]))
                else:
                    res.append(ItemFamily(od, current_class))
            return res

l_item_families = ItemFamily.load_item_family_list()

"""Maps item 3 letter codes to durability, armor class min, armor class max. As encoded in armor_weapons.tsv."""
d_armor_weapons = dict()  # type: Dict[str, Tuple[int, int, int]]

def load_armor_weapons_dict():
    """Reads the given armor-weapon file and exposes it as a dict with item code as key and a 3-tuple
    of (durability, ac min, ac max) as value."""
    pfname = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'armor_weapons.tsv')
    if not os.path.isfile(pfname):
        _log.warning(f"Failure to open armor weapons file '{pfname}' for reading.")
        return
    d_armor_weapons.clear()
    with open(pfname, 'r') as IN:
        for line in IN:
            if re.findall("^\\s*#", line) or re.findall("^\\s*$", line):
                continue  # << Ignore comment and empty lines.
            line = re.split("\t", line, maxsplit=4)
            code = line[0]
            if len(line) < 4 or len(code) != 3:
                continue
            try:
                durability = int(line[1])
                ac_min = int(line[2])
                ac_max = int(line[3])
            except ValueError:
                _log.warning(f"Invalid line encountered: {line}")
                continue
            d_armor_weapons[code] = durability, ac_min, ac_max

load_armor_weapons_dict()

class E_Rune(Enum):
    ER_NORUNE = 0
    ER_EL = 1
    ER_ELD = 2
    ER_TIR = 3
    ER_NEF = 4
    ER_ETH = 5
    ER_ITH = 6
    ER_TAL = 7
    ER_RAL = 8
    ER_ORT = 9
    ER_THUL = 10
    ER_AMN = 11
    ER_SOL = 12
    ER_SHAEL = 13
    ER_DOL = 14
    ER_HEL = 15
    ER_IO = 16
    ER_LUM = 17
    ER_KO = 18
    ER_FAL = 19
    ER_LEM = 20
    ER_PUL = 21
    ER_UM = 22
    ER_MAL = 23
    ER_IST = 24
    ER_GUL = 25
    ER_VEX = 26
    ER_OHM = 27
    ER_LO = 28
    ER_SUR = 29
    ER_BER = 30
    ER_JAH = 31
    ER_CHAM = 32
    ER_ZOD = 33

    ER_TOPAZ_CHIPPED = 40
    ER_AMETHYST_CHIPPED = 41
    ER_SAPHIRE_CHIPPED = 42
    ER_RUBY_CHIPPED = 43
    ER_EMERALD_CHIPPED = 44
    ER_DIAMOND_CHIPPED = 45
    ER_SKULL_CHIPPED = 46

    ER_TOPAZ_FLAWED = 50
    ER_AMETHYST_FLAWED = 51
    ER_SAPHIRE_FLAWED = 52
    ER_RUBY_FLAWED = 53
    ER_EMERALD_FLAWED = 54
    ER_DIAMOND_FLAWED = 55
    ER_SKULL_FLAWED = 56

    ER_TOPAZ = 60
    ER_AMETHYST = 61
    ER_SAPHIRE = 62
    ER_RUBY = 63
    ER_EMERALD = 64
    ER_DIAMOND = 65
    ER_SKULL = 66

    ER_TOPAZ_FLAWLESS = 70
    ER_AMETHYST_FLAWLESS = 71
    ER_SAPHIRE_FLAWLESS = 72
    ER_RUBY_FLAWLESS = 73
    ER_EMERALD_FLAWLESS = 74
    ER_DIAMOND_FLAWLESS = 75
    ER_SKULL_FLAWLESS = 76

    ER_TOPAZ_PERFECT = 80
    ER_AMETHYST_PERFECT = 81
    ER_SAPHIRE_PERFECT = 82
    ER_RUBY_PERFECT = 83
    ER_EMERALD_PERFECT = 84
    ER_DIAMOND_PERFECT = 85
    ER_SKULL_PERFECT = 86

    @property
    def type_code(self) -> Optional[str]:
        if self.value == 0:
            return None
        if 1 <= self.value <= 33:
            return "r{0:02d}".format(self.value)

        gem_reference = E_Rune(self.value % 10 + 60)
        quality = floor(self.value / 10) - 4
        if quality < 0:
            quality = 0
        elif quality > 4:
            quality = 4
        if gem_reference == E_Rune.ER_TOPAZ:
            return ['gcy', 'gfy', 'gsy', 'gly', 'gpy'][quality]
        elif gem_reference == E_Rune.ER_AMETHYST:
            return ['gcv', 'gfv', 'gsv', 'gzv', 'gpv'][quality]
        elif gem_reference == E_Rune.ER_SAPHIRE:
            return ['gcb', 'gfb', 'gsb', 'glb', 'gpb'][quality]
        elif gem_reference == E_Rune.ER_RUBY:
            return ['gcr', 'gfr', 'gsr', 'glr', 'gpr'][quality]
        elif gem_reference == E_Rune.ER_EMERALD:
            return ['gcg', 'gfg', 'gsg', 'glg', 'gpg'][quality]
        elif gem_reference == E_Rune.ER_DIAMOND:
            return ['gcw', 'gfw', 'gsw', 'glw', 'gpw'][quality]
        elif gem_reference == E_Rune.ER_SKULL:
            return ['skc', 'skf', 'sku', 'skl', 'skz'][quality]
        else:
            return None

    @staticmethod
    def from_name(name: str) -> Optional[E_Rune]:
        """:param name: Simply by rune name for runes Else /^[tasredb][0-4]$/ for gems and skulls (bone0-4, get it?),
          the number denoting the quality from 0: chipped to 4: perfect."""
        # > Grand case 1: Gems and Bones (i.e., Skulls). -------------
        m = re.findall("^([tasredb])([0-4])$", name.lower())
        if m:
            tp = m[0][0]
            quality = floor(int(m[0][1]))
            if quality < 0:
                quality = 0
            elif quality > 4:
                quality = 4
            val = 40 + quality * 10
            if tp == 't':
                val += 0
            elif tp == 'a':
                val += 1
            elif tp == 's':
                val += 2
            elif tp == 'r':
                val += 3
            elif tp == 'e':
                val += 4
            elif tp == 'd':
                val += 5
            elif tp == 'b':
                val += 6
            else:
                return None
            return E_Rune(val)
        # < ----------------------------------------------------------
        # > Runes. ---------------------------------------------------
        try:
            candidate = E_Rune[f"ER_{name}".upper()]
        except KeyError:
            _log.warning(f"Invalid rune name '{name}' encountered.")
            return None
        return candidate if 1 <= candidate.value <= 33  else None
    # < --------------------------------------------------------------

    @staticmethod
    def sample_byte_code_rune_el() -> bytes:
        """:returns byte code of a rune El, located in row 0, column 0 of the Horadric Cube."""
        return b'JM\x10\x00\xa0\x00e\x00\x00(\x07\x13\x03\x02'


class E_Mercenary(Enum):
    """Mercenary data type."""
    EM_NONE = 0
    IS_DEAD = 1 # << [177:179]  0: alive, 1: dead
    SEED = 2 # << [179:183]
    ID_NAME = 3 # << [183:185]
    TYPE = 4 # << [185:187]
    EXPERIENCE = 5  # << [187:191]  Encodes experience in plain 4 byte little endian.


class E_Progression(Enum):
    """Which is the adequate level of difficulty? Lives repeating bits 0-1 into 6-7"""
    EP_NORMAL = 0      # <<   0 + 0
    EP_NIGHTMARE = 5  # <<  64 + 1
    EP_HELL = 10      # << 128 + 2
    EP_MASTER = 15    # << 192 + 3

    def __str__(self) -> str:
        return re.sub('^EP_', '', self.name).lower()

class E_Attributes(Enum):
    AT_STRENGTH = 0
    AT_ENERGY = 1
    AT_DEXTERITY = 2
    AT_VITALITY = 3
    AT_UNUSED_STATS = 4
    AT_UNUSED_SKILLS = 5
    AT_CURRENT_HP = 6
    AT_MAX_HP = 7
    AT_CURRENT_MANA = 8
    AT_MAX_MANA = 9
    AT_CURRENT_STAMINA = 10
    AT_MAX_STAMINA = 11
    AT_LEVEL = 12
    AT_EXPERIENCE = 13
    AT_GOLD = 14
    AT_STASHED_GOLD = 15
    AT_UNSPECIFIED = 16

    def get_attr_sz_bits(self) -> int:
        val = self.value
        if val <= 4:
            return 10
        elif val == 5:
            return 8
        elif val <= 11:
            return 21 # << This is True! However, only the most significant 13 bit are integer. The first most significant 2 of the remaining byte count quarter points.
        elif val == 12:
            return 7
        elif val == 13:
            return 32
        elif val <= 15:
            return 25
        elif val == 16:
            return 0
        else:
            _log.warning(f"Unknown attribute ID {val} encountered! Returning -1.")
            return -1

    def has_quarter_prefix_byte(self) -> bool:
        """
        :returns True if and only if the attribute has quarters, a rudimentary floating point support for
        0/4,..,3/4. This means HP, MANA, and STAMINA attributes. They are prefixed a byte of the structure
        ab000000, where ab counts the number of quarters. 00=0/4, 01=1/4, 10=2/4, 11=3/4."""
        return self.value == 21


class E_Characters(Enum):
    EC_AMAZON = 0
    EC_SORCERESS = 1
    EC_NECROMANCER = 2
    EC_PALADIN = 3
    EC_BARBARIAN = 4
    EC_DRUID = 5
    EC_ASSASSIN = 6
    EC_UNSPECIFIED = 7

    def is_female(self) -> bool:
        return (self == E_Characters.EC_AMAZON) or (self == E_Characters.EC_SORCERESS) or (self == E_Characters.EC_ASSASSIN)

    def starting_attributes(self) -> OrderedDict[E_Attributes, int]:
        """:returns the core attribute starting values for this character.
        Note, that HP, Mana and Stamina are not listed. This is on purpose. These values can be computed."""
        if self == E_Characters.EC_AMAZON:
            return odict([(E_Attributes.AT_STRENGTH, 20), (E_Attributes.AT_ENERGY, 15), (E_Attributes.AT_DEXTERITY, 25), (E_Attributes.AT_VITALITY, 20)])
        elif self == E_Characters.EC_SORCERESS:
            return odict([(E_Attributes.AT_STRENGTH, 10), (E_Attributes.AT_ENERGY, 35), (E_Attributes.AT_DEXTERITY, 25), (E_Attributes.AT_VITALITY, 10)])
        elif self == E_Characters.EC_NECROMANCER:
            return odict([(E_Attributes.AT_STRENGTH, 15), (E_Attributes.AT_ENERGY, 25), (E_Attributes.AT_DEXTERITY, 25), (E_Attributes.AT_VITALITY, 15)])
        elif self == E_Characters.EC_PALADIN:
            return odict([(E_Attributes.AT_STRENGTH, 25), (E_Attributes.AT_ENERGY, 15), (E_Attributes.AT_DEXTERITY, 20), (E_Attributes.AT_VITALITY, 25)])
        elif self == E_Characters.EC_BARBARIAN:
            return odict([(E_Attributes.AT_STRENGTH, 30), (E_Attributes.AT_ENERGY, 10), (E_Attributes.AT_DEXTERITY, 20), (E_Attributes.AT_VITALITY, 25)])
        elif self == E_Characters.EC_DRUID:
            return odict([(E_Attributes.AT_STRENGTH, 15), (E_Attributes.AT_ENERGY, 20), (E_Attributes.AT_DEXTERITY, 20), (E_Attributes.AT_VITALITY, 25)])
        elif self == E_Characters.EC_ASSASSIN:
            return odict([(E_Attributes.AT_STRENGTH, 20), (E_Attributes.AT_ENERGY, 25), (E_Attributes.AT_DEXTERITY, 20), (E_Attributes.AT_VITALITY, 20)])
        else:
            raise ValueError(f"Unsupported character code {self.value} encountered. Unable to determine starting attributes.")

    @staticmethod
    def _float2tuple(val: float) -> Tuple[int, int]:
        main = round(floor(val))
        quarters = round((val - main) * 4.0)
        return main, quarters


    def effect_of_attribute_points(self, attr: E_Attributes, n: int = 1) -> OrderedDict[E_Attributes, Tuple[int, int]]:
        """:returns the delta on HP, Stamina and Mana of a given attribute point spent into that attribute."""
        res = odict()  # type: OrderedDict[E_Attributes, Tuple[int, int]]
        res[E_Attributes.AT_MAX_HP] = 0, 0
        res[E_Attributes.AT_MAX_MANA] = 0, 0
        res[E_Attributes.AT_MAX_STAMINA] = 0, 0

        if self in [E_Characters.EC_AMAZON, E_Characters.EC_PALADIN]:
            if attr == E_Attributes.AT_VITALITY:
                res[E_Attributes.AT_MAX_HP] = 3 * n, 0
                res[E_Attributes.AT_MAX_STAMINA] = 1 * n, 0
            elif attr == E_Attributes.AT_ENERGY:
                res[E_Attributes.AT_MAX_MANA] = self._float2tuple(1.5 * n)

        if self in [E_Characters.EC_SORCERESS, E_Characters.EC_NECROMANCER, E_Characters.EC_DRUID]:
            if attr == E_Attributes.AT_VITALITY:
                res[E_Attributes.AT_MAX_HP] = 2 * n, 0
                res[E_Attributes.AT_MAX_STAMINA] = 1 * n, 0
            elif attr == E_Attributes.AT_ENERGY:
                res[E_Attributes.AT_MAX_MANA] = 2 * n, 0

        if self == E_Characters.EC_BARBARIAN:
            if attr == E_Attributes.AT_VITALITY:
                res[E_Attributes.AT_MAX_HP] = 4 * n, 0
                res[E_Attributes.AT_MAX_STAMINA] = 1 * n, 0
            if attr == E_Attributes.AT_ENERGY:
                res[E_Attributes.AT_MAX_MANA] = 1 * n, 0

        if self == E_Characters.EC_ASSASSIN:
            if attr == E_Attributes.AT_VITALITY:
                res[E_Attributes.AT_MAX_HP] = 3 * n, 0
                res[E_Attributes.AT_MAX_STAMINA] = self._float2tuple(1.25 * n)
            if attr == E_Attributes.AT_ENERGY:
                res[E_Attributes.AT_MAX_MANA] = self._float2tuple(1.75 * n)

        return res

    def __str__(self) -> str:
        s = re.sub('^EC_', '', self.name).lower()
        return s[0].upper() + s[1:]


class E_Waypoint(Enum):
    EW_ROGUE_ENCAMPMENT = 0
    EW_COLD_PLAINS = 1
    EW_STONY_FIELD = 2
    EW_DARK_WOOD = 3
    EW_BLACK_MARSH = 4
    EW_OUTER_CLOISTER = 5
    EW_JAIL_L1 = 6
    EW_INNER_CLOISTER = 7
    EW_CATACOMBS_L2 = 8
    EW_LUT_GHOLEIN = 9
    EW_SEWERS_L2 = 10
    EW_DRY_HILLS = 11
    EW_HALLS_OF_THE_DEAD_L2 = 12
    EW_FAR_OASIS = 13
    EW_LOST_CITY = 14
    EW_PALACE_CELLAR = 15
    EW_ARCANE_SANCTUARY = 16
    EW_CANYON_OF_THE_MAGI = 17
    EW_KURAST_DOCKS = 18
    EW_SPIDER_FOREST = 19
    EW_GREAT_MARSH = 20
    EW_FLAYER_JUNGLE = 21
    EW_LOWER_KURAST = 22
    EW_KURAST_BAZAAR = 23
    EW_UPPER_KURAST = 24
    EW_TRAVINCAL = 25
    EW_DURANCE_OF_HATE_L2 = 26
    EW_PANDEMONIUM_FORTRESS = 27
    EW_CITY_OF_THE_DAMNED = 28
    EW_RIVER_OF_FLAMES = 29
    EW_HARROGATH = 30
    EW_FRIGID_HIGHLANDS = 31
    EW_ARREAT_PLATEAU = 32
    EW_CRYSTALLINE_PASSAGE = 33
    EW_GLACIAL_TRAL = 34
    EW_HALLS_OF_PAIN = 35
    EW_FROZEN_TUNDRA = 36
    EW_THE_ANCIENTS_WAY = 37
    EW_WORLDSTONE_KEEP_L2 = 38
    EW_NONE = 39

    @staticmethod
    def get_index_data(progression: E_Progression) -> Tuple[int, int]:
        """:returns the byte index limits within the binary total data that holds
        the 5 bytes with the waypoint information for the given level of progression."""
        if progression == E_Progression.EP_NORMAL:
            return 643, 648
        elif progression == E_Progression.EP_NIGHTMARE:
            return 667, 672
        elif progression == E_Progression.EP_HELL:
            return 691, 696
        raise ValueError(f"Unsupported progression level: '{progression}'")

    @staticmethod
    def get_waypoints_from_bm(bm: str, *, enabled: bool = True) -> List[E_Waypoint]:
        res = list()  # List[E_Waypoint]
        n = len(bm)
        for j in range(39):
            val = bm[j] if j < n else '0'
            if (val == '0' and not enabled) or (val == '1' and enabled):
                res.append(E_Waypoint(j))
        return res

    @property
    def index_act(self) -> int:
        if 0 <= self.value < 9:
            return 0
        elif 9 <= self.value < 18:
            return 1
        elif 18 <= self.value < 27:
            return 2
        elif 27 <= self.value < 30:
            return 3
        elif 30 <= self.value < 39:
            return 4
        return -1

    @property
    def is_in_town(self) -> bool:
        return self.value in (0, 9, 18, 27, 30)

    def __str__(self) -> str:
        if self == E_Waypoint.EW_THE_ANCIENTS_WAY:
            return "The Ancients' Way"
        elts = self.name.split('_')[1:]
        for j in range(len(elts)):
            elts[j] = elts[j].lower()
            if len(elts[j]) > 3:
                elts[j] = elts[j][0].upper() + elts[j][1:]
        return ' '.join(elts)

class E_Quest(Enum):
    """Code is the position in bytes, beginning after the quest 10-byte header (Woo!) at byte 345.
    Convention: A double __ in an enum name shall signify an apostrophe."""
    EQ_NONE = 0

    EQ_DEN_OF_EVIL = 2
    EQ_SISTERS___BURIAL_GROUNDS = 4
    EQ_SEARCH_FOR_CAIN = 6
    EQ_THE_FORGOTTEN_TOWER = 8
    EQ_TOOLS_OF_THE_TRADE = 10
    EQ_SISTERS_TO_THE_SLAUGHTER = 12

    EQ_RADAMENT__S_LAIR = 18
    EQ_THE_HORADRIC_STAFF = 20
    EQ_TAINTED_SUN = 22
    EQ_ARCANE_SANCTUARY = 24
    EQ_THE_SUMMONER = 26
    EQ_THE_SEVEN_TOMBS = 28

    EQ_THE_GOLDEN_BIRD = 34
    EQ_BLADE_OF_THE_OLD_RELIGION = 36
    EQ_KHALIM__S_WILL = 38
    EQ_LAM_ESEN__S_TOME = 40
    EQ_THE_BLACKENED_TEMPLE = 42
    EQ_THE_GUARDIAN = 44

    EQ_FALLEN_ANGEL = 50
    EQ_HELL__S_FORGE = 52
    EQ_TERROR__S_END = 54

    EQ_SIEGE_ON_HARROGATH = 70
    EQ_RESCUE_ON_MOUNT_ARREAT = 72
    EQ_PRISON_OF_ICE = 74
    EQ_BETRAYAL_IN_HARROGATH = 76
    EQ_RITE_OF_PASSAGE = 78
    EQ_EVE_OF_DESTRUCTION = 80

    @staticmethod
    def get_enum_entry_by_index(index: int):
        """:returns the indexth quest in the list. Ignores EQ_NONE.
        :raises ValueError(..) if index is either too large or <0."""
        entries = [e for e in E_Quest][1:]  # << First entry is EQ_NONE.
        if index < 0 or index >= len(entries):
            raise ValueError(f"Impossible index '{index}'. There are {len(entries)} quests in total.")
        return entries[index]

    def pos_byte(self, difficulty: E_Progression) -> int:
        """:returns the first byte of this quest given difficulty level."""
        if difficulty == E_Progression.EP_NORMAL:
            addendum = 0
        elif difficulty == E_Progression.EP_NIGHTMARE:
            addendum = 96
        else:  # Hell and Master.
            addendum = 2 * 96
        return self.value + addendum + 345

    def set_quest(self, data: bytes, difficulty: E_Progression, complete_rather_than_reset: bool):
        """Set quest to either done or untouched.
        :param data: Whole-save-game as a large bytes data block.
        :param difficulty: Difficulty level intended for quest data altering.
        :param complete_rather_than_reset: If True, will set the quest to 1000000000001000, else 0000000000000000.
        :returns a copy of the given whole-save-game-data with altered quest-data."""
        val = int.to_bytes(2**12 + 1, 2, 'little', signed = False) if complete_rather_than_reset else b'\x00\x00'
        pos = self.pos_byte(difficulty)
        return data[:pos] + val + data[(pos+2):]

    def __str__(self) -> str:
        s = self.name[3:]
        s = s.replace('__', "'")
        wordlets = ['OF', 'FOR', 'THE', 'TO', 'ON', 'IN']
        res = ' '.join([x.lower() if x in wordlets else (x[0].upper() + x[1:].lower()) for x in s.split('_')])
        return res[0].upper() + res[1:]

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

    @property
    def is_header(self) -> bool:
        return self in (E_ItemBlock.IB_PLAYER_HD, E_ItemBlock.IB_CORPSE_HD, E_ItemBlock.IB_MERCENARY_HD, E_ItemBlock.IB_IRONGOLEM_HD)


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

    @property
    def size(self) -> Tuple[int, int]:
        """The Horadric Cube is 4x3. The Stash is 8x6. The inventory is 4x10."""
        if self == E_ItemStorage.IS_CUBE:
            return 4,3
        elif self == E_ItemStorage.IS_STASH:
            return 8,6
        elif self == E_ItemStorage.IS_INVENTORY:
            return 4,10
        return 0,0

    def __str__(self) -> str:
        return re.sub("^IS_", "", self.name).lower()


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


class E_ItemBitProperties(Enum):
    """Boolean property bit sites taken from https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#single-item-layout
    Item.get_item_property(..) may be used to query these bits."""
    IP_NONE = 0
    IP_IDENTIFIED = 20
    IP_BROKEN = 24
    IP_SOCKETED = 27
    IP_NEWLY_FOUND = 29
    IP_STARTER_GEAR = 33
    IP_COMPACT = 37  #<< i.e., there is no extended information to this item. These appear to have 112 bits, i.e. 14 bytes.
    IP_ETHEREAL = 38
    IP_PERSONALIZED = 40
    IP_RUNEWORD = 42


    def __str__(self) -> str:
        return re.sub("^IP_", "", self.name, flags=re.IGNORECASE).lower()


d_skills = {
    E_Characters.EC_AMAZON: ["Magic Arrow", "Fire Arrow", "Inner Sight", "Critical Strike", "Jab",
                             "Cold Arrow", "Multiple Shot", "Dodge", "Power Strike", "Poison Javelin",
                             "Exploding Arrow", "Slow Missiles", "Avoid", "Impale", "Lightning Bolt",
                             "Ice Arrow", "Guided Arrow", "Penetrate", "Charged Strike", "Plague Javelin",
                             "Strafe", "Immolation Arrow", "Decoy", "Evade", "Fend",
                             "Freezing Arrow", "Valkyrie", "Pierce", "Lightning Strike", "Lightning Fury"],
    E_Characters.EC_SORCERESS: ["Fire Bolt", "Warmth", "Charged Bolt", "Ice Bolt", "Frozen Armor",
                                "Inferno", "Static Field", "Telekinesis", "Frost Nova", "Ice Blast",
                                "Blaze", "Fireball", "Nova", "Lightning", "Shiver Armor",
                                "Fire Wall", "Enchant", "Chain Lightning", "Teleport", "Glacial Spike",
                                "Meteor", "Thunder Storm", "Energy Shield", "Blizzard", "Chilling Armor",
                                "Fire Mastery", "Hydra", "Lightning Mastery", "Frozen Orb", "Cold Mastery"],
    E_Characters.EC_NECROMANCER: ["Amplify Damage", "Teeth", "Bone Armor", "Skeleton Mastery", "Raise Skeleton",
                                  "Dim Vision", "Weaken", "Poison Dagger", "Corpse Explosion", "Clay Golem",
                                  "Iron Maiden", "Terror", "Bone Wall", "Golem Mastery", "Skeletal Mage",
                                  "Confuse", "Life Tap", "Poison Explosion", "Bone Spear", "Blood Golem",
                                  "Attract", "Decrepify", "Bone Prison", "Summon Resist", "Iron Golem",
                                  "Lower Resist", "Poison Nova", "Bone Spirit", "Fire Golem", "Revive"],
    E_Characters.EC_PALADIN: ["Sacrifice", "Smite", "Might", "Prayer", "Resist Fire",
                              "Holy Bolt", "Thorns", "Holy Fire", "Defiance", "Resist Cold",
                              "Zeal", "Charge", "Blessed Aim", "Cleansing", "Resist Lightning",
                              "Vengeance", "Blessed Hammer", "Concentration", "Holy Freeze", "Vigor",
                              "Conversion", "Holy Shield", "Holy Shock", "Sanctuary", "Meditation",
                              "Fist of the Heavens", "Fanaticism", "Conviction", "Redemption", "Salvation"],
    E_Characters.EC_BARBARIAN: ["Bash", "Sword Mastery", "Axe Mastery", "Mace Mastery", "Howl", "Find Potion",
                                "Leap", "Double Swing", "Polearm Mastery", "Throwing Mastery", "Spear Mastery", "Taunt", "Shout",
                                "Stun", "Double Throw", "Increased Stamina", "Find Item",
                                "Leap Attack", "Concentrate", "Iron Skin", "Battle Cry",
                                "Frenzy", "Increased Speed", "Battle Orders", "Grim Ward",
                                "Whirlwind", "Berserk", "Natural Resistance", "War Cry", "Battle Command"],
    E_Characters.EC_DRUID: ["Raven", "Poison Creeper", "Werewolf", "Lycanthropy", "Firestorm",
                            "Oak Sage", "Summon Spirit Wolf", "Werebear", "Molten Boulder", "Arctic Blast",
                            "Carrion Wine", "Feral Rage", "Maul", "Fissure", "Cyclone Armor",
                            "Heart of Wolverine", "Summon Dire Wolf", "Rabies", "Fire Claws", "Twister",
                            "Solar Creeper", "Hunger", "Shockwave", "Volcano", "Tornado",
                            "Spirit of Barbs", "Summon Grizzly", "Fury", "Armageddon", "Hurricane"],
    E_Characters.EC_ASSASSIN: ["Fire Blast", "Claw Mastery", "Psychic Hammer", "Tiger Strike", "Dragon Talon",
                               "Shock Web", "Blade Sentinel", "Burst of Speed", "Fists of Fire", "Dragon Claw",
                               "Charged Bolt Sentry", "Wake of Fire", "Weapon Block", "Cloak of Shadows", "Cobra Strike",
                               "Blade Fury", "Fade", "Shadow Warrior", "Claws of Thunder", "Dragon Tail",
                               "Lightning Sentry", "Wake of Inferno", "Mind Blast", "Blades of Ice", "Dragon Flight",
                               "Death Sentry", "Blade Shield", "Venom", "Shadow Master", "Phoenix Strike"]
}


# > Properties for the god mode. -------------------------------------
d_god_attr = odict([
    (E_Attributes.AT_STRENGTH, 400),
    (E_Attributes.AT_ENERGY, 400),
    (E_Attributes.AT_DEXTERITY, 400),
    (E_Attributes.AT_VITALITY, 400),
    (E_Attributes.AT_UNUSED_STATS, 0),
    (E_Attributes.AT_UNUSED_SKILLS, 5),
    (E_Attributes.AT_CURRENT_HP, 307200), # << encoded 1200 (see Data.HMS_encode(..) below)
    (E_Attributes.AT_MAX_HP, 307200), # << encoded 1200
    (E_Attributes.AT_CURRENT_MANA, 307200), # << encoded 1200
    (E_Attributes.AT_MAX_MANA, 307200), # << encoded 1200
    (E_Attributes.AT_CURRENT_STAMINA, 102400), # << encoded 400
    (E_Attributes.AT_MAX_STAMINA, 102400) # << encoded 400
])  # type: OrderedDict[E_Attributes, int]
# [Note: For restoring purposes skills are handled with skills. They are not counted in the god_attr sum.]
sum_god_attr = d_god_attr[E_Attributes.AT_STRENGTH] +\
    d_god_attr[E_Attributes.AT_ENERGY]+\
    d_god_attr[E_Attributes.AT_DEXTERITY]+\
    d_god_attr[E_Attributes.AT_VITALITY]+\
    d_god_attr[E_Attributes.AT_UNUSED_STATS]

d_god_skills = [18] * 30  # type: List[int]
sum_god_skills = sum(d_god_skills) + d_god_attr[E_Attributes.AT_UNUSED_SKILLS]
# < ------------------------------------------------------------------

# > Horadric Cube. ---------------------------------------------------
"""Binary block describing a horadric cube in the top left of the backpack inventory."""
data_tpl_horadric_cube = b'JM\x10\x00\x80\x00e\x00\x00"\xf6\x86\x07\x028\xce1\xff\x86\xe0?'
# < ------------------------------------------------------------------

# > items of adornment. ----------------------------------------------
class E_ItemTpl(Enum):
    IT_UNSPECIFIED = 0
    IT_JEWEL = 1
    IT_CHARM = 2
    IT_AMULET = 3
    IT_RING = 4

"""Non magic simple items."""
d_data_tpl = {
    E_ItemTpl.IT_JEWEL : b'JM\x10\x00\x80\x00e\x00\x00\xa8Vv\x07\x82\x00\x9dL\xf6\x92,\xff\x01',
    E_ItemTpl.IT_RING  : b'JM\x10\x00\x80\x00e\x00\x00(\x97\xe6\x06\x02?L\xd2,\x9f\x04\xff\x01',
    E_ItemTpl.IT_AMULET: b'JM\x10\x00\x80\x00e\x00 \x18\xd6V\x07\x82\x1f\x8b\xe3-\x98\x04\xff\x01',
    E_ItemTpl.IT_CHARM : b'JM\x10\x00\x80\x00e\x00@8\xd6\x16\x03\x02f\xd0\r\xb5\x9e\x0c\x00\xf0\x1f'
}

"""Rare Ring 'Storm Loop'"""
ring_rare_tpl = b'JM\x10\x00\x80\x00e\x00\x00(\x97\xe6\x06\x82/e\xccE\x8f\x85\xd4\xbd\xef\xe8\x8a\xd48\x8c\x88Y\x11\x0bN&|`!\x80!\x90\x82\xe9\x89\x9f4\x1eP\x81\xff'
# < ------------------------------------------------------------------


def bytes2bitmap(data: bytes) -> str:
    return '{:0{width}b}'.format(int.from_bytes(data, 'little'), width = len(data) * 8)

def bitmap2bytes(bitmap: str) -> bytes:
    n = len(bitmap)
    if (n % 8) != 0:
        raise ValueError(f"Invalid bitmap length {n} not being a multiple of 8.")
    return int(bitmap,2).to_bytes(round(n/8), 'little')

def prefix_bitmap_to_8_product(bitmap: str, *, delete_leading_zeros: bool = True) -> str:
    """Drop leading zeros. Then prefix zeros until len(bm) % 8 == 0."""
    if delete_leading_zeros:
        bitmap = re.sub("^0*", "", bitmap)
    if len(bitmap) % 8:
        bitmap = '0' * (8 - len(bitmap) % 8) + bitmap
    return bitmap

def get_range_from_bitmap(bitmap: str, index_start: int, index_end: int, *, do_invert: bool = False) -> Optional[int]:
    # Note: Being numerals the left-most entries in the bitmap are the most significant!
    #  However, our indexing schema asks for little endian. Hence, when accessing the bitmap,
    #  we have to invert the indices to start on the right side of the numeral.
    #  Thus, the index [start:end] becomes [n-end:n-start].]
    n = len(bitmap)
    bm = bitmap[(n-index_end):(n-index_start)]
    if len(bm) == 0:
        return None
    return int(bm[::-1] if do_invert else bm, 2)

def set_range_to_bitmap(bitmap: str, index_start: int, index_end: int, val: int, *, do_invert: bool = False) -> str:
    width = index_end - index_start
    if width == 0:
        return bitmap  # << Nothing to do.
    rg = '{:0{width}b}'.format(val, width=width)
    if len(rg) > width:
        raise ValueError(f"Encountered range '{rg}' of length {len(rg)}. However, width <= {width} was expected.")
    if do_invert:
        rg = rg[::-1]
    n = len(bitmap)
    return bitmap[0:n-index_end] + rg + bitmap[n-index_start:]

def get_bitrange_value_from_bytes(data: bytes, index_start: int, index_end: int, *, do_invert: bool = False):
    bm = bytes2bitmap(data)
    return get_range_from_bitmap(bm, index_start, index_end, do_invert=do_invert)

def set_bitrange_value_to_bytes(data: bytes, index_start: int, index_end: int, val: int, *, do_invert: bool = False) -> bytes:
    bm = bytes2bitmap(data)
    bm = set_range_to_bitmap(bm, index_start, index_end, val, do_invert=do_invert)
    return bitmap2bytes(bm)


class Mod_BitShape:
    """For the socket science project. Mods are at the end of an item, merely followed by the
    0x1ff item end code and a 0-padding filling up the final byte. Mods are explained in
    https://github.com/WalterCouto/D2CE/blob/main/source/res/TXT/global/excel/itemstatcost.txt
    and there seem to have the general name prefix 'item_'."""
    def __init__(self, id_9bit: int, len_data_bit: int, is_signed: bool, name: str, *,
                 is_mod_superior_weapon: bool = False, is_mod_superior_armor: bool = False):
        """:param is_mod_superior_weapon: Is this mod one of the mods associated with superior weapons?
        :param is_mod_superior_armor: Is this mod one of the mods associated with superior armor?
        """
        self.id_9bit = id_9bit  # type: int
        self.len_data_bit = len_data_bit  # type: int
        self.is_signed = is_signed  # type: bool
        self.name = name  # type: str
        self.is_mod_superior_weapon = is_mod_superior_weapon  # type: bool
        self.is_mod_superior_armor = is_mod_superior_armor  # type: bool

    @property
    def regexp_binary_code(self):
        """:returns forward binary code regexp for this bit shape. Apply to forward bitmap."""
        return r'.' * self.len_data_bit + '{:0{width}b}'.format(self.id_9bit, width=9)

    def __str__(self):
        prefix_signed = '' if self.is_signed else 'un'
        return f'{self.name} ({prefix_signed}signed, 9+{self.len_data_bit} bit): {self.regexp_binary_code[::-1]}'

"""On superior weapons and armor: https://diablo.fandom.com/wiki/Superior_Items"""
known_mods = [
    Mod_BitShape(16, 9, True, 'item_armor_percent', is_mod_superior_armor=True),
    Mod_BitShape(75, 7, True, 'item_maxdurability_percent', is_mod_superior_weapon=True, is_mod_superior_armor=True),
    Mod_BitShape(17, 9, True, 'item_maxdamage_percent', is_mod_superior_weapon=True),
    Mod_BitShape(18, 9, True, 'item_mindamage_percent'),
    Mod_BitShape(22, 7, True, 'maxdamage', is_mod_superior_weapon=True),
    Mod_BitShape(68, 7, True, 'attackrate', is_mod_superior_weapon=True),
    Mod_BitShape(78, 7, False, 'item_attackertakesdamage')
]  # type: List[Mod_BitShape]


class E_Quality(Enum):
    """https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#quality"""
    EQ_NONE = 100
    EQ_INFERIOR = 1  # Followed by 3 bits in the Quality Attributes section later on.
    EQ_NORMAL = 2  # Followed by 12 bits if this is a charm, else by 0 bits.
    EQ_SUPERIOR = 3  # Followed by 0.
    EQ_MAGICALLY_ENHANCED = 4  # Followed by 22 bits (11 for prefix, 11 for suffix)
    EQ_SET = 5  # Followed by 12 bit set id.
    EQ_RARE = 6  # Followed by 16 bits (8 for prefix, 8 for suffix)
    EQ_UNIQUE = 7  # Followed by 12 bit unique bits.
    EQ_CRAFT = 8  # Followed by 2 blocks of length 1 if bit 1 is not set or of length 12 otherwise. So, in {2, 13, 24}
    #EQ_TEMPERED = 9  # Tempered. Like Craft of attributes length {2, 13, 24}.

    def __str__(self):
        return re.sub("^eq_", "", self.name.lower()) + f"({self.value})"

class E_InferiorQuality(Enum):
    EQ_NONE = 100
    EQ_CRUDE = 0
    EQ_CRACKED = 1
    EQ_DAMAGED = 2
    EQ_LOW_QUALITY = 3

class E_ExtProperty(Enum):
    """Extended item properties that are not covered by above. They begin at bit 108. After that it becomes complicated.
    Order of the enum follows the order of the entries in the extended section.
    Invaluable source: https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md#extended-item-data"""
    EP_QUEST_SOCKETS = 1  # At bits [108:111]
    EP_QUALITY = 2  # at bits [150:154] says [2] (at bit [111:115] says [1])
    EP_CUSTOM_GRAPHICS = 3  # 1 or 4, depending on first bit.  I.e., 4 bit, if bit 1 is set, else 1 bit.
    EP_CLASS_SPECIFIC = 4  # 1 or 12, depending on first bit.
    EP_QUALITY_ATTRIBUTES = 5  # Quality Attributes. Complicated list depending on value of Quality above.
    EP_RUNEWORD = 6  # 16 bit or 0, depending on whether this is a rune word item. 12 first bits encode rune word name.
    EP_PERSONALIZATION = 7  # 105 bits of personalization name as written by Anya.
    EP_TOMES = 8  # 5 bits if this is a tomes item. 0 else.
    EP_REALM = 9  # 1 bit if first bit is 0, else 97 bit for misc items, gems, charms and runes, else 4.
    EP_DEFENSE = 10  # 0 bit if this is not armor. Else 11.
    EP_DURABILITY = 11  # 8 bit if weapon or armor, showing max durability. If current dur>0, 9 more bits follow.
    EP_STACK = 12  # 9 bits counting the stack size if this item is stackable. 0 else.
    EP_SET = 13  # 5 bits if this is a set item. 0 else.
    EP_SOCKETS = 14  # 4 bits if this is a socketed item. Counts the sockets. 0 bit else.
    EP_MODS = 15  # Modifications. 9+ bits. Terminated by 0x1ff.
    EP_MODS_RUNEWORD = 16  # Modifications in a secondary mods block. Specialized for Runewords.

    def __str__(self):
        return re.sub("^ep_", "", self.name.lower())


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
        :param index_start byte index in the complete file where this item starts.
        :param index_end byte index int the complete file one point beyond where this item ends.
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

    @data_item.setter
    def data_item(self, bts: bytes):
        if self.is_analytical:
            return
        else:
            self.data = self.data[0:self.index_start] + bts + self.data[self.index_end:]

    def get_item_property(self, prop: E_ItemBitProperties) -> Optional[bool]:
        """:returns None, if this Item is analytical or otherwise too short.
        Else True if the ItemProperty bit in question is 1, and False if it is 0."""
        if self.is_analytical:
            return None
        val = prop.value
        if (len(self.data_item) * 8) < val:
            return False
        return True if get_range_from_bitmap(bytes2bitmap(self.data_item), val, val+1) else False

    def copy_with_item_property_set(self, prop: E_ItemBitProperties, enabled: bool) -> Optional[bytes]:
        """Copies this item's byte string, and sets the given value to the given item property."""
        if self.is_analytical:
            return None
        val = prop.value
        if (len(self.data_item) * 8) < val:
            return
        bm = bytes2bitmap(self.data_item)
        # bm = bm[0:val] + ('1' if enabled else '0') + bm[(val+1):]
        bm = set_range_to_bitmap(bm, val, val+1, 1 if enabled else 0)
        return bitmap2bytes(bm)

    @property
    def col(self) -> Optional[int]:
        """Bits 65,..,68"""
        if self.is_analytical:
            return None
        return get_range_from_bitmap(bytes2bitmap(self.data_item), 65, 69)

    @col.setter
    def col(self, c: int):
        if self.is_analytical:
            return
        self.data_item = set_bitrange_value_to_bytes(self.data_item, 65, 69, c)

    @property
    def row(self) -> Optional[int]:
        """Bits 69,..,71"""
        if self.is_analytical:
            return None
        return get_range_from_bitmap(bytes2bitmap(self.data_item), 69, 72)

    @row.setter
    def row(self, r: int):
        if self.is_analytical:
            return
        self.data_item = set_bitrange_value_to_bytes(self.data_item, 69, 72, r)

    @property
    def stash_type(self) -> Optional[E_ItemStorage]:
        if self.is_analytical:
            return None
        rg = get_range_from_bitmap(bytes2bitmap(self.data_item), 73, 76)
        return E_ItemStorage.IS_UNSPECIFIED if not rg else E_ItemStorage(rg)

    @stash_type.setter
    def stash_type(self, code: E_ItemStorage):
        if self.is_analytical:
            return
        self.data_item = set_bitrange_value_to_bytes(self.data_item, 73, 76, code.value)

    @property
    def type_code(self) -> Optional[str]:
        if self.is_analytical:
            return None
        bm = bytes2bitmap(self.data_item)[::-1]
        if len(bm) < 106:
            return None  # No item with type code.
        l1 = chr(int(bm[76:84][::-1], 2))
        l2 = chr(int(bm[84:92][::-1], 2))
        l3 = chr(int(bm[92:100][::-1], 2))
        return l1 + l2 + l3

    @property
    def type_name(self) -> Optional[str]:
        tn = ItemFamily.get_name_by_code(self.type_code)
        return f"unknown type code '{self.type_code}'" if tn is None else tn

    @type_code.setter
    def type_code(self, code: str):
        if (not code) or (len(code) != 3):
            _log.warning(f"Item Code string needs to be 3 characters exactly. '{code}' was given.")
            return
        if self.is_analytical:
            return
        bm = bytes2bitmap(self.data_item)
        if len(bm) < 106:
            return  # No item with type code.
        val = ord(code[0]) + (ord(code[1]) << 8) + (ord(code[2]) << 16)
        self.data_item = set_bitrange_value_to_bytes(self.data_item, 76, 100, val)

    @property
    def is_charm(self) -> Optional[bool]:
        """:returns True if and only if this item is a small, large or grand charm."""
        tc = self.type_code
        if tc is None:
            return None
        return self.type_code in ('cm1', 'cm2', 'cm3')

    @property
    def is_magic(self) -> Optional[bool]:
        """:returns True if and only if this item is magically enhanced, rare, set or unique."""
        return self.quality in (E_Quality.EQ_MAGICALLY_ENHANCED, E_Quality.EQ_RARE, E_Quality.EQ_SET, E_Quality.EQ_UNIQUE)

    @property
    def is_ethereal(self) -> Optional[bool]:
        return self.get_item_property(E_ItemBitProperties.IP_ETHEREAL)

    @is_ethereal.setter
    def is_ethereal(self, enable: bool):
        if self.is_analytical or not (self.is_weapon or self.is_armor):
            return
        is_eth = self.get_item_property(E_ItemBitProperties.IP_ETHEREAL)
        if is_eth is None or is_eth == enable:
            return  # << Nothing to do.
        #dur_cur, dur_max = self.durability
        dur_max = self.durability[1]
        ac = self.defense
        # https://diablo.fandom.com/wiki/Ethereal_Items_(Diablo_II)
        if ac is not None:
            ac = round(ac * (1.5 if enable else 0.67))
        if enable:
            #dur_cur = round(dur_cur / 2.0 + 1)
            dur_max = round(dur_max / 2.0 + 1)
        else:
            #dur_cur = round((dur_cur-1) * 2.0)
            dur_max = round((dur_max-1) * 2.0)
        self.data_item = self.copy_with_item_property_set(E_ItemBitProperties.IP_ETHEREAL, enable)
        if ac is not None:
            self.defense = ac
        self.durability = dur_max

    @property
    def is_armor(self) -> Optional[bool]:
        if self.is_analytical:
            return None
        fam = ItemFamily.get_family_by_code(self.type_code)
        return fam.is_armor if fam else None

    @property
    def is_weapon(self) -> Optional[bool]:
        if self.is_analytical:
            return None
        fam = ItemFamily.get_family_by_code(self.type_code)
        return fam.is_weapon if fam else None

    @property
    def is_stack(self) -> Optional[bool]:
        if self.is_analytical:
            return None
        fam = ItemFamily.get_family_by_code(self.type_code)
        return fam.is_stack if fam else None

    @property
    def volume(self) -> Optional[Tuple[int, int]]:
        """:returns rows and cols this item takes up at most in inventory."""
        if self.is_analytical:
            return None
        fam = ItemFamily.get_family_by_code(self.type_code)
        if fam is None:
            return None
        return fam.rows, fam.cols

    @property
    def is_set(self) -> Optional[bool]:
        if self.is_analytical:
            return None
        return False if self.quality is None else self.quality == E_Quality.EQ_SET

    @property
    def item_class(self) -> Optional[E_ItemClass]:
        if self.is_analytical:
            return None
        fam = ItemFamily.get_family_by_code(self.type_code)  # type: Optional[ItemFamily]
        return fam.item_class if fam else None

    @property
    def item_grade(self) -> Optional[E_ItemGrade]:
        """:returns this item's grade. Normal, Exceptional, Elite, or Post-Elite."""
        if self.is_analytical:
            return None
        return ItemFamily.get_grade_for_code(self.type_code)  # type: Optional[E_ItemGrade]

    @item_grade.setter
    def item_grade(self, grade: E_ItemGrade):
        if self.is_analytical:
            return
        code = ItemFamily.get_sibling_code_for_grade(self.type_code, grade)
        self.type_code = code

    @property
    def item_parent(self) -> Optional[E_ItemParent]:
        """Simple items Version 96: Bits 58-60"""
        if self.is_analytical:
            return None
        if len(self.data_item) < 8:
            return E_ItemParent.IP_UNSPECIFIED
        val = get_bitrange_value_from_bytes(self.data_item, 58, 61)
        try:
            return E_ItemParent(val)
        except ValueError:
            _log.warning(f"Invalid parent code {val} encountered.")
            return E_ItemParent.IP_UNSPECIFIED

    @item_parent.setter
    def item_parent(self, parent: E_ItemParent):
        if self.is_analytical:
            return
        bm = bytes2bitmap(self.data_item)
        bm = set_range_to_bitmap(bm, 58, 61, parent.value)
        self.data_item = bitmap2bytes(bm)

    @property
    def item_equipped(self) -> Optional[E_ItemEquipment]:
        """61-64"""
        if self.is_analytical:
            return None
        data_item = self.data_item
        if len(data_item) < 9:
            return E_ItemEquipment.IE_UNSPECIFIED
        bm = bytes2bitmap(data_item)
        val = get_range_from_bitmap(bm, 61, 65)
        try:
            return E_ItemEquipment(val)
        except ValueError:
            _log.warning(f"Encountered weird equipment code {val} on item of type '{self.type_code}'.")
            return E_ItemEquipment.IE_UNSPECIFIED

    @property
    def item_level(self) -> Optional[int]:
        """:returns the ilevel of this object if such extended information is available. Else None."""
        if self.is_analytical:
            return None
        bm = bytes2bitmap(self.data_item)
        if len(bm) < 150:
            return None
        return get_range_from_bitmap(bm, 143, 150)  # << [2] states 7 bits volume [143:150]. However, [144:150] seems better.

    @item_level.setter
    def item_level(self, ilevel: int):
        if self.is_analytical or ilevel < 0:
            return
        if ilevel > 99:
            ilevel = 99
        bm = bytes2bitmap(self.data_item)
        if len(bm) < 150:
            return
        bm = set_range_to_bitmap(bm, 143, 150, ilevel)
        self.data_item = bitmap2bytes(bm)

    @property
    def quality(self) -> Optional[E_Quality]:
        if self.is_analytical:
            return None
        bm = bytes2bitmap(self.data_item)
        if len(bm) < 155:
            return E_Quality.EQ_NONE
        # Jarulf describes how the quality bits will start at bit 150 rather than 111. See [2].
        val = get_range_from_bitmap(bm, 150, 154)
        try:
            return E_Quality(val)
        except ValueError:
            _log.warning(f"Invalid quality value '{val}' encountered in item of tp '{self.type_code}'.")
            return E_Quality.EQ_NONE

    @property
    def personalization(self) -> Optional[str]:
        """:returns None if this item has not been personalized by Anya. Else the personalization name."""
        if self.is_analytical or not self.get_item_property(E_ItemBitProperties.IP_PERSONALIZED):
            return None
        index0, index1 = self.get_extended_item_index()[E_ExtProperty.EP_PERSONALIZATION]
        bm = bytes2bitmap(self.data_item)[::-1]
        bm_short = bm[index0:index1]
        # [Note: The letters are encoded in 7-bit Ascii.]
        while len(bm_short) % 7 != 0:
            bm_short += '0'
        res = ""
        n = round(len(bm_short) / 8)
        for j in range(n):
            bm_letter = bm_short[(j*7):((j+1)*7)][::-1]
            c = chr(int(bm_letter,2))
            if c == '\x00':
                break
            else:
                res += c
        return res

    @property
    def defense(self) -> Optional[int]:
        val = self.get_extended_item_int_value(E_ExtProperty.EP_DEFENSE)
        # [Note: For some reason val seems to be encoded +10 in bits. Are there armors with defense == -10?]
        if val is not None:
            val = val - 10
        return val

    @defense.setter
    def defense(self, val: int):
        index_ext = self.get_extended_item_index()
        if index_ext is None or val is None or E_ExtProperty.EP_DEFENSE not in index_ext:
            return
        index = index_ext[E_ExtProperty.EP_DEFENSE]
        if index[1] - index[0] != 11:
            return
        # [Note: For some reason the armor value is saved as 10 points below the true value.]
        val += 10
        if val >= 2**11:
            val = (2**11) - 1
        elif val <= 10:
            return
        bvalr = ('{:0{width}b}'.format(val, width = 11))[::-1]
        bmr = bytes2bitmap(self.data_item)[::-1]
        bmr = bmr[:index[0]] + bvalr + bmr[index[1]:]
        bm = prefix_bitmap_to_8_product(bmr[::-1])
        self.data_item = bitmap2bytes(bm)

    @property
    def durability(self) -> Optional[Tuple[int,int]]:
        """:returns int Tuple (current durability/maximum durability) for this Item. Or None if not applicable."""
        val = self.get_extended_item_int_value(E_ExtProperty.EP_DURABILITY)
        if val is None:
            return None
        else:
            return (val >> 8), (val & 255)

    @durability.setter
    def durability(self, dur: int):
        """Sets current/max durability of this item to ac_max/ac_max.
        :param dur in 1..255. If anywhere else, nothing will be done."""
        if self.is_analytical or dur is None or dur <= 0 or dur > 255:
            return
        index_ext = self.get_extended_item_index()
        if E_ExtProperty.EP_DURABILITY not in index_ext:
            return
        index = index_ext[E_ExtProperty.EP_DURABILITY]
        if (index[1] - index[0]) != 17:
            _log.warning(f"Durability extended section expected to be of 17 bit length. However, index does not reflect that: {index}.")
            return
        val_max = '{:0{width}b}'.format(dur, width = 8)
        val_current = '{:0{width}b}'.format(dur, width = 9)  #<< yes. 9.
        val = val_max[::-1] + val_current[::-1]
        bmr = bytes2bitmap(self.data_item)[::-1]
        bmr = bmr[:index[0]] + val + bmr[index[1]:]
        self.data_item = bitmap2bytes(bmr[::-1])

    def durability2default(self):
        """Sets this items durability to the default defined by armor_weapons.tsv."""
        code = self.type_code
        if not code in d_armor_weapons:
            return
        self.durability = d_armor_weapons[code][0]

    def defense2default(self, p: float = 0.5):
        """Sets this item's armor value (if any is present) to (p * ac_max + (1-p) * ac_min)."""
        code = self.type_code
        if not code in d_armor_weapons:
            return
        val = round((1.0 - p) * d_armor_weapons[code][1] + p * d_armor_weapons[code][2])  # type: int
        self.defense = val

    @property
    def stack(self) -> Optional[int]:
        return self.get_extended_item_int_value(E_ExtProperty.EP_STACK)

    @property
    def n_sockets(self) -> Optional[int]:
        if self.is_analytical:
            return None
        ns = self.get_extended_item_int_value(E_ExtProperty.EP_SOCKETS)
        return ns if ns else 0

    @property
    def n_sockets_occupied(self):
        if self.is_analytical:
            return None
        qs = self.get_extended_item_int_value(E_ExtProperty.EP_QUEST_SOCKETS)
        if qs is None:
            return 0
        if self.item_class == E_ItemClass.IC_QUEST_ITEMS:
            # Only the highest bits encodes number of occupied sockets (yes, there may be only 1 if at all).
            qs = qs & 4
        return qs

    @n_sockets_occupied.setter
    def n_sockets_occupied(self, val: int) -> Optional[int]:
        """:param val: New int value. in {0,..,self.n_sockets}
        Will set this item's number of occupied sockets to the requested value. Respects the quest item special rule,
        preserving the lower 2 of the 3 bits if this is a quest item.
        Warning! This is a dangerous function, acting only on itself. Ensure consistency of following
        socketed items by setting their stash types to STORE and their parentage to whatever stash type is
        appropriate."""
        if self.is_analytical:
            return
        if val < 0:
            val = 0
        elif val > self.n_sockets:
            val = self.n_sockets
        qs = self.get_extended_item_int_value(E_ExtProperty.EP_QUEST_SOCKETS)
        if self.item_class == E_ItemClass.IC_QUEST_ITEMS:
            # Preserve the lower 2 bits, they are quest-related.
            qs &= 3
            qs += 4 if val else 0
        else:
            qs = val
        bmr_qs = '{:0{width}b}'.format(qs, width=3)[::-1]
        index = self.get_extended_item_index()[E_ExtProperty.EP_QUEST_SOCKETS]
        bmr = bytes2bitmap(self.data_item)[::-1]
        bmr = bmr[:index[0]] + bmr_qs + bmr[index[1]:]
        self.data_item = bitmap2bytes(bmr[::-1])

    @property
    def is_socketable(self) -> Optional[bool]:
        return self.item_class.is_socketable

    def get_known_mods(self, *, is_mod_superior_weapon: bool = False, is_mod_superior_armor: bool = False) -> Optional[List[Dict[str, Any]]]:
        """:returns List of Dicts of Mod_BitShapes from known_mods that have been found in the item.
        Keys: index0, index1: data_item forward bit index of the mod. mod: ModBitShape."""
        if self.is_analytical:
            return None
        if self.get_item_property(E_ItemBitProperties.IP_COMPACT):
            return list()
        ext_index = self.get_extended_item_index()
        index0_mods = ext_index[E_ExtProperty.EP_MODS][0]
        bmr = bytes2bitmap(self.data_item)[::-1][index0_mods:]
        mods = list()  # type: List[Dict[str, Mod_BitShape]]
        index_offset = 0
        found_anything = True
        while found_anything:
            found_anything = False
            for km in known_mods:
                if (is_mod_superior_weapon and not km.is_mod_superior_weapon) or (is_mod_superior_armor and not km.is_mod_superior_armor):
                    continue
                regexp = km.regexp_binary_code[::-1]
                ms = [(m.start(0), m.end(0)) for m in re.finditer(regexp, bmr[index_offset:])]
                if ms and ms[0][0] == 0:
                    mods.append(
                        {
                            'index0': ms[0][0] + index0_mods + index_offset,
                            'index1': ms[0][1] + index0_mods + index_offset,
                            'mod': km,
                            'bmr': bmr[ms[0][0]:ms[0][1]]
                        }
                    )
                    index_offset += ms[0][1]
                    found_anything = True
                    break
        return mods

    def known_mods_to_str(self) -> str:
        """:returns the list of known mods found within this item as a human-readable string."""
        mods = self.get_known_mods()
        if not mods:
            return "No known mods recognized."
        res = ''
        for mod in mods:
            res += f"\n{mod['mod']} [{mod['index0']}:{mod['index1']}]"
        return res

    def get_extended_item_index(self) -> Optional[Dict[E_ExtProperty, Tuple[int,int]]]:
        """Sophisticated function for determining the index0, index1 intervals for each extended item property."""
        if self.is_analytical or self.get_item_property(E_ItemBitProperties.IP_COMPACT):
            return None
        res = {
            E_ExtProperty.EP_QUEST_SOCKETS: (108, 111),
            E_ExtProperty.EP_QUALITY: (150, 154)
        }
        index_bit = 154
        bm = bytes2bitmap(self.data_item)
        item_class = self.item_class  # type: E_ItemClass

        try:
            sz_custom_graphics = 4 if get_range_from_bitmap(bm, index_bit, index_bit+1) > 0 else 1
        except Exception as err:
            print (f"Error encountered while trying to get range for custom graphics: {str(err)}")
            return res
        res[E_ExtProperty.EP_CUSTOM_GRAPHICS] = index_bit, (index_bit + sz_custom_graphics)
        index_bit = index_bit + sz_custom_graphics

        sz_class_specific = 12 if get_range_from_bitmap(bm, index_bit, index_bit+1) > 0 else 1
        res[E_ExtProperty.EP_CLASS_SPECIFIC] = index_bit, (index_bit + sz_class_specific)
        index_bit = index_bit + sz_class_specific

        quality = self.quality
        val_len = 0
        if quality == E_Quality.EQ_NONE:
            val_len = 0
        elif quality == E_Quality.EQ_INFERIOR:
            val_len = 3
        elif quality == E_Quality.EQ_NORMAL:
            val_len = 12 if self.is_charm else 0
        elif quality == E_Quality.EQ_SUPERIOR:
            val_len = 3
        elif quality == E_Quality.EQ_MAGICALLY_ENHANCED:
            val_len = 22
        elif quality == E_Quality.EQ_SET:
            val_len = 12
        elif quality in (E_Quality.EQ_RARE, E_Quality.EQ_CRAFT):
            val_len = 16
            for j in range(6):
                key_bit = get_range_from_bitmap(bm, index_bit + val_len, index_bit + val_len + 1)
                sz_affix = 1 if key_bit == 0 else 12
                if len(bm) <= val_len + sz_affix:
                    _log.warning(f"{quality} item has an extended section that seems to be too small for its magic attributes. This hints at a bug.")
                else:
                    val_len += sz_affix
        elif quality == E_Quality.EQ_UNIQUE:
            val_len = 12
        elif quality == E_Quality.EQ_CRAFT:
            len0 = 12 if get_range_from_bitmap(bm, index_bit, index_bit + 1) else 1
            len1 = 12 if get_range_from_bitmap(bm, index_bit + len0, index_bit + len0 + 1) else 1
            val_len = len0 + len1
        res[E_ExtProperty.EP_QUALITY_ATTRIBUTES] = index_bit, (index_bit + val_len)
        index_bit = index_bit + val_len

        sz_runeword = 16 if self.get_item_property(E_ItemBitProperties.IP_RUNEWORD) else 0
        res[E_ExtProperty.EP_RUNEWORD] = index_bit, (index_bit + sz_runeword)
        index_bit = index_bit + sz_runeword

        sz_personalization = 0
        if self.get_item_property(E_ItemBitProperties.IP_PERSONALIZED):
            # Personalization is encoded in 7-bit ASCII and stopped by a traditional 0-entry.
            # [Note: Do not use self.personalization here, lest you enter an infinite recursion!]
            sz_personalization = 0
            bmp = bm[::-1][index_bit:(index_bit+105)]
            while bmp[sz_personalization:(sz_personalization + 7)] != '0000000':
                # current_char = chr(int(bmp[sz_personalization:(sz_personalization + 7)][::-1],2))
                sz_personalization = sz_personalization + 7
            sz_personalization = sz_personalization + 7
        res[E_ExtProperty.EP_PERSONALIZATION] = index_bit, (index_bit + sz_personalization)
        index_bit = index_bit + sz_personalization

        sz_tome = 5 if item_class == E_ItemClass.IC_TOMES else 0
        res[E_ExtProperty.EP_TOMES] = index_bit, (index_bit + sz_tome)
        index_bit = index_bit + sz_tome

        if get_range_from_bitmap(bm, index_bit, index_bit + 1) < 1:
            sz_realm = 1
        elif item_class in [E_ItemClass.IC_MISC, E_ItemClass.IC_GEMS, E_ItemClass.IC_CHARMS, E_ItemClass.IC_RUNES]:
            sz_realm = 97
        else:
            sz_realm = 4
        res[E_ExtProperty.EP_REALM] = index_bit, (index_bit + sz_realm)
        index_bit = index_bit + sz_realm

        sz_armor = 11 if self.is_armor else 0
        res[E_ExtProperty.EP_DEFENSE] = index_bit, (index_bit + sz_armor)
        index_bit = index_bit + sz_armor

        if not (self.is_armor or self.is_weapon):
            sz_durability = 0
        elif get_range_from_bitmap(bm, index_bit, index_bit + 8) == 0:
            sz_durability = 8
        else:
            sz_durability = 17
        res[E_ExtProperty.EP_DURABILITY] = index_bit, (index_bit + sz_durability)
        index_bit = index_bit + sz_durability

        sz_stack = 9 if self.is_stack else 0
        res[E_ExtProperty.EP_STACK] = index_bit, (index_bit + sz_stack)
        index_bit = index_bit + sz_stack

        sz_set = 5 if self.is_set else 0
        res[E_ExtProperty.EP_SET] = index_bit, (index_bit + sz_set)
        index_bit = index_bit + sz_set

        sz_sockets = 4 if self.get_item_property(E_ItemBitProperties.IP_SOCKETED) else 0
        res[E_ExtProperty.EP_SOCKETS] = index_bit, (index_bit + sz_sockets)
        index_bit += sz_sockets

        is_runeword = self.get_item_property(E_ItemBitProperties.IP_RUNEWORD)
        sz_mods = 0
        bmr = bm[::-1]
        if is_runeword:
            # It may be that the item is superior. Use known mods codes to determine site of '111111111' terminator.
            # A superior item may have one or two modifiers of total length 18 or 16 each. So possible lengths are:
            # {16, 18, 32, 34, 36}. After that the '111111111' terminator follows.
            for l in (0,16,18,32,34,36):
                if re.search('^' + '.'*l + '111111111', bmr[index_bit:(index_bit+45)]) is not None:
                    sz_mods = l
                    break
            res[E_ExtProperty.EP_MODS] = index_bit, (index_bit + sz_mods)
            index_bit += sz_mods + 9
        else:
            index_end = index_bit
            if index_end % 8 > 0:
                index_end = index_end + 8 - index_end % 8
            sz_intermezzo = 0
            while index_end <= len(bmr):
                try:
                    gps = re.search("^(.*?)(1111111110*)$", bmr[index_bit:index_end]).groups()
                    sz_mods = len(gps[0])
                    sz_intermezzo = len(gps[1])
                    break
                except AttributeError:
                    index_end += 8
            res[E_ExtProperty.EP_MODS] = index_bit, (index_bit + sz_mods)
            index_bit += sz_mods + sz_intermezzo

        res[E_ExtProperty.EP_MODS_RUNEWORD] = len(bmr), len(bmr)
        index_end = len(bmr)
        if index_bit < len(bmr):
            try:
                gps = re.search("^(.*)1111111110*$", bmr[index_bit:index_end]).groups()
                sz_mods_rw = len(gps[0])
                res[E_ExtProperty.EP_MODS_RUNEWORD] = index_bit, index_bit + sz_mods_rw
            except AttributeError:
                _log.warning(f"Strange runeword mods section '{bmr[index_bit:]} encountered.'")
        return res

    def get_extended_item_int_value(self, prop_ext: E_ExtProperty) -> Optional[int]:
        """Convenience function for getting a specific value from an extended item index.
        :param prop_ext: The extended property in question.
        :returns the value associated with the extended property as int. Or None, in case of failure."""
        indices = self.get_extended_item_index()
        if indices is None or prop_ext not in indices:
            return None
        bm = bytes2bitmap(self.data_item)
        index0, index1 = indices[prop_ext]
        return get_range_from_bitmap(bm, index0, index1)

    def get_extended_item_index_as_str(self) -> str:
        """Debugging function, turning the extended item index into something human-readable."""
        if self.is_analytical:
            return "Analytical item has no extended section."
        indices = self.get_extended_item_index()
        if indices is None:
            return "No extended item index."
        res = ""
        bmr = bytes2bitmap(self.data_item)[::-1]
        for key in indices:
            res += f"  {key}: [{indices[key][0]}:{indices[key][1]}], {bmr[indices[key][0]:indices[key][1]]}"
            if key != E_ExtProperty.EP_MODS_RUNEWORD:
                res += "\n"
        return res

    @staticmethod
    def drop_empty_block_indices(block_indices: Dict[E_ItemBlock, Tuple[int, int]]) -> Dict[E_ItemBlock, Tuple[int, int]]:
        # Drop empty blocks.
        deletees = list()  # type: List[E_ItemBlock]
        for key in block_indices:
            if (block_indices[key])[0] == (block_indices[key])[1]:
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
                # We have found the corpse header. 20 bytes. I.e., 2 bytes 'JM' + 2 bytes 'is_alive' + 16 bytes corpse header.
                # Hence, additionally to the 16 bytes we want to include 'JM..' into the header.
                delta_corpse_hd = 20 if ((index_end - index_start) == 16) else 4
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
        Each 3 tuple. Entries 0 and 1 index one item, thus that data[index_start:index_end] encompasses the entire
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

    def get_block_items(self, block: Optional[E_ItemBlock] = E_ItemBlock.IB_UNSPECIFIED,
                          parent: Optional[E_ItemParent] = E_ItemParent.IP_UNSPECIFIED,
                          equipped: Optional[E_ItemEquipment] = E_ItemEquipment.IE_UNSPECIFIED,
                          stored: Optional[E_ItemStorage] = E_ItemStorage.IS_UNSPECIFIED) -> List[Item]:
        """Get a list of items that matches all given filters. If everything is unspecified, all items are returned.
        However, if a parameter is given as None, that property will be ignored.
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
                   (stored in [E_ItemStorage.IS_UNSPECIFIED, item.stash_type]):
                    res.append(item)
        return res

    def get_cube_contents(self) -> List[Item]:
        """:returns list of items and socketed items found in the Horadric Cube."""
        items = self.get_block_items(E_ItemBlock.IB_PLAYER)
        found_cube = False
        res = list()  # type: List[Item]
        # [Note: Horadric cube items may be parents to children following them. These children will then
        #  have E_ItemParent.IP_ITEM. This holds true, e.g., for socketed runes.
        #  Also, it is (contrary to earlier assumption) not a given that all CUBE items are consecutive.]
        for item in items:
            if item.stash_type == E_ItemStorage.IS_CUBE:
                found_cube = True
            if not found_cube:
                continue
            if item.stash_type == E_ItemStorage.IS_CUBE or item.item_parent == E_ItemParent.IP_ITEM:
                res.append(item)
            else:
                found_cube = False
        return res

    def get_index1(self, index0):
        """Tool function. Given an index0, pointing at a b'JM' item starting code.
        :param index0: Some item starting index pointing at a 'JM'. Not necessarily the 'JM' for this self.
        :return the index1 that goes with it. Meaning: The item lives in self.data[index0:index1].
          This does not include items that may be socketed into it."""
        if self.data[index0:(index0+2)] != b'JM':
            _log.warning(f"Given index0=={index0} does not point at a b'JM' marker.")
            return None
        index1 = index0 + 14  # << 112 bit would mean a compact item. Compare bit 37.
        if len(self.data) < index1 or self.data[(index0+4):(index0+6)] == b'JM':
            return index0 + 4  # << Section marker pseudo-item.
        item_proto = Item(self.data[index0:index1], 0, 14)
        is_compact = item_proto.get_item_property(E_ItemBitProperties.IP_COMPACT)
        if is_compact:
            return index1
        index_sufficient = len(re.split(b'JM', self.data[index0+2:],maxsplit=1)[0]) + 2 + index0
        bm_extended = bytes2bitmap(self.data[index0:index_sufficient])
        # A compact item really has only 106 bit. The rest to the 14 bytes is padding.
        finds = re.findall('.'*106 + ".*?111111111", bm_extended[::-1])  # type: List[str]
        if not finds:
            _log.warning(f"Non-compact item without extended section terminator encountered at index0 == {index0}.")
            return index1
        index1 = index0 + ceil(len(finds[0]) / 8.0)
        return index1

    def get_next_item(self) -> Optional[Item]:
        """:returns the next item if it exists and is not a section separator."""
        if self.is_analytical:
            return None
        index1 = self.get_index1(self.index_end)
        if index1 - self.index_end < 14:  # << Shorter than a compact item.
            return None
        else:
            return Item(self.data, self.index_end, index1, self.item_block, self.index_item_block + 1)

    def get_item_dismantled(self) -> Optional[List[Item]]:
        """:returns a list holding this item and any item that is socketed into it."""
        if self.is_analytical:
            return None
        res = [self]  # type: List[Item]
        n_sockets_occupied = self.n_sockets_occupied
        if not n_sockets_occupied:
            return res
        item = self
        for j in range(n_sockets_occupied):
            item = item.get_next_item()
            if item.item_parent == E_ItemParent.IP_ITEM:
                res.append(item)
            else:
                break
        return res

    @staticmethod
    def create_rune(name: E_Rune, stash_type = E_ItemStorage.IS_CUBE, row: int = 0, col: int = 0) -> Optional[Item]:
        """Creates an 'JM...' byte string with the specified rune.
        :param name: Which rune is to be created?
        :param stash_type: Where is the rune stored?
        :param row: Row index in storage.
        :param col: Column index in storage.
        [Note: The rune type is determined by the item code. This is a list of 3 eight-bit letters.
          Consider a simple item's bitmap. Reverse order (little endian style) binary string of bit [76:106] of
          the binary representation of an "JM"-starting item, potentially representing a rune.
          It will be split into three letters:
          * Bits [0:8]: Letter 1. Always an 'r': '01001110'==114=='r' (reversed!)
          * Bits [8:16]: Letter 2, and
          * Bits[16:24]: Letter 3. These are numbers. From '01' to '33'. The digits:
            '00001100' == '0', '10001100' == '1', '01001100' == '2', '11001100' == '3', '00101100' == '4',
            '10101100' == '5', '01101100' == '6', '11101100' == '7', '00011100' == '8', '10011100' == '9'.]"""
        if isinstance(name, str):
            try:
                name = E_Rune.from_name(name)
            except KeyError:
                _log.warning(f"Invalid rune name string: '{name}'. Returning None.")
                return None
        if name.type_code is None:
            _log.warning(f"Invalid rune designation: '{name}'. Returning None.")
        rune_el = E_Rune.sample_byte_code_rune_el()  # type: bytes
        item_rune = Item(rune_el, index_start=0, index_end=len(rune_el))
        item_rune.stash_type = stash_type
        item_rune.col = col
        item_rune.row = row
        item_rune.type_code = name.type_code
        return item_rune

    def toStringShort(self) -> str:
        """:return Short, human-readable one-line representation of this item."""
        if self.is_analytical:
            return "Analytic Item"
        parts = list()  # type: List[str]
        quality = self.quality
        if quality == E_Quality.EQ_MAGICALLY_ENHANCED:
            parts.append("magic")
        elif quality in (E_Quality.EQ_SET, E_Quality.EQ_CRAFT, E_Quality.EQ_RARE, E_Quality.EQ_UNIQUE):
            parts.append(quality.__str__().replace('_', ' '))

        if self.is_ethereal:
            parts.append('ethereal')

        if self.item_grade != E_ItemGrade.IG_NORMAL:
            parts.append(self.item_grade.__str__().replace('_', ' '))

        if self.item_class and self.item_class not in (E_ItemClass.IC_MISC, E_ItemClass.IC_RUNES, E_ItemClass.IC_GEMS, E_ItemClass.IC_SCROLLS, E_ItemClass.IC_CHARMS):
            parts.append(re.sub("s$", '', self.item_class.__str__(), count=1, flags=re.IGNORECASE))

        if self.n_sockets:
            sock_type = 'rw' if self.get_item_property(E_ItemBitProperties.IP_RUNEWORD) else 's'
            parts.append(f'{sock_type}:{self.n_sockets_occupied}/<={self.n_sockets}')

        if self.item_level is not None:
            parts.append(f"ilevel {self.item_level}")

        desc = ' (' + ', '.join(parts) + ')' if parts else ''
        return self.type_name + desc

    def __str__(self) -> str:
        if self.is_analytical:
            return "Analytic Item instance."
        elif self.item_block.is_header:
            code = self.item_block
            if code == E_ItemBlock.IB_PLAYER_HD:
                return "=== Player ========================================================="
            elif code == E_ItemBlock.IB_CORPSE_HD:
                return "=== Corpse ========================================================="
            elif code == E_ItemBlock.IB_MERCENARY_HD:
                return "=== Mercenary ======================================================"
            elif code == E_ItemBlock.IB_IRONGOLEM_HD:
                return "=== Iron Golem ====================================================="
            else:
                return "===================================================================="
        else:
            props = ""
            for prop in E_ItemBitProperties:
                val = prop.value
                if not val:
                    continue
                props += f"{prop}: {self.get_item_property(prop)}, "

            bm = bytes2bitmap(self.data_item)[::-1]
            bl = len(bm)

            classification = f"{self.item_grade}, armor: {self.is_armor}, weapon: {self.is_weapon}, sockets: {self.n_sockets_occupied}/{self.n_sockets}, stack: {self.is_stack}, set: {self.is_set}"
            known_mods_str = self.known_mods_to_str()
            if known_mods_str:
                known_mods_str += "\n"

            dur = self.durability
            if dur is None:
                dur = 'n.a.'
            else:
                dur = f"{dur[0]}/{dur[1]}"

            bm_col_row_split = f"{bm[:65]} {bm[65:69]} {bm[69:72]} {bm[72:76]} {bm[76:144]} {bm[144:150]} {bm[150:154]} {bm[154:]}"
            return f"Item '{self.type_name}' ({len(self.data_item)} bytes) ({classification}) {self.item_block.name} #{self.index_item_block} personalization: '{self.personalization}', index: ({self.index_start}, {self.index_end})\n" \
                f"Max size in inventory: {self.volume}, Defense (base): {self.defense}, Durability (base): {dur}, Stack: {self.stack},\n" \
                f"Parent: {self.item_parent.name}, Storage: {self.stash_type.name}, (r:{self.row}, c:{self.col}), Equip: {self.item_equipped.name}\n" \
                f"{props}\ntype code: {self.type_code}, quality: {self.quality}, ilevel: {self.item_level}, is charm: {self.is_charm}, Bit length: {bl} ({bl/8} bytes)\n" \
                f"{known_mods_str}" \
                f"{self.get_extended_item_index_as_str()}\n" \
                f"{bm_col_row_split}\n{self.data_item}"


class Data:
    """Data object concerned with the binary content of the entirety of a .d2s save game file."""
    def __init__(self, pfname: str, pname_backup: Optional[str] = None):
        """:param pfname: Path and filename to target .d2s save game file."""
        if not pfname:
            raise ValueError("pfname required for Data object.")
        self.pfname = pfname
        self.pname_backup = os.path.expanduser(pname_backup if pname_backup else os.path.dirname(pfname))
        with open(os.path.expanduser(pfname), 'rb') as IN:
            self.data = IN.read()
        ver = self.get_file_version()
        if ver != 96:
            print(f"""Invalid save game version '{ver}'. Sorry. This script so far only supports version code '96' (v1.10-v1.14d) save game files.
Fixing this is mostly updating the sites in the .d2s file, where the action takes place. At the time of writing
this page was an excellent source for that: https://github.com/WalterCouto/D2CE/blob/main/d2s_File_Format.md""")
            sys.exit(1)

    def __eq__(self, other: Data) -> bool:
        """Two Data blocks are deemed equal if their pfnames match."""
        return self.pfname == other.pfname

    def __ne__(self, other: Data) -> bool:
        return self.pfname != other.pfname

    def get_file_version(self) -> int:
        """File version. Encoded into main header bytes [4:8]. Value 96 is for versions 1.10-1.14d."""
        bm = bytes2bitmap(self.data[4:8])
        return get_range_from_bitmap(bm, 0, 16)

    @property
    def has_horadric_cube(self) -> bool:
        for item in Item(self.data).get_block_items(E_ItemBlock.IB_PLAYER):
            if item.type_code == 'box':
                return True
        return False

    @property
    def has_iron_golem(self) -> bool:
        item_analysis = Item(self.data)
        hd = item_analysis.get_block_items(E_ItemBlock.IB_IRONGOLEM_HD)
        if not hd:
            return False
        data = hd[0].data_item[2]
        return data > 0

    @property
    def level_by_header(self) -> int:
        """Character level in main header. This is not to be confused with the E_Attributes.AT_LEVEL, the
        actual in-game character level. level_by_header is used for display on the character selection screen.
        However, as a matter of policy, both values should match."""
        return self.data[43]

    @level_by_header.setter
    def level_by_header(self, value: int):
        self.data = self.data[:43] + int.to_bytes(value, 1, 'little') + self.data[44:]

    def get_quests(self, difficulty: E_Progression) -> Dict[E_Quest, bytes]:
        res = dict()
        quests = [q for q in E_Quest][1:]  # << Ignore leading EQ_NONE.
        for quest in quests:
            pos = quest.pos_byte(difficulty)
            res[quest] = self.data[pos:(pos+2)]
        return res

    def get_quests_simplified(self) -> Dict[E_Progression, str]:
        """:returns a bitmap with a bit for each quest. 0 means quest is 0 completely. Else 1. Aims at displays."""
        res = dict()  # type: Dict[E_Progression, str]
        quests = [q for q in E_Quest][1:]  # << Ignore leading EQ_NONE.
        for difficulty in [E_Progression.EP_NORMAL, E_Progression.EP_NIGHTMARE, E_Progression.EP_HELL]:
            s = ''
            for quest in quests:
                pos = quest.pos_byte(difficulty)
                s = s + ('0' if (self.data[pos:(pos+2)] == b'\x00\x00') else '1')
            res[difficulty] = s
        return res

    def set_quests_simplified(self, codes: Dict[E_Progression, str]):
        quests = [q for q in E_Quest][1:]  # << Ignore leading EQ_NONE.
        for difficulty in codes:
            if difficulty == E_Progression.EP_MASTER:
                continue
            code = re.sub("[^0-1]", '.', codes[difficulty])
            for j in range(min(len(code), len(quests))):
                if code[j] not in '01':
                    continue
                self.data = quests[j].set_quest(self.data, difficulty, code[j] == '1')

    @property
    def waypoint_map(self) -> Dict[E_Progression, str]:
        """:returns bitmaps for the activated waypoints (little endian) for each level of difficulty.
        Strings are in order of the game and acts. Acts 1,2,3,5 have 9 bits each, act 4 has only 3.
        Since there are 40 bit in 5 bytes, but only 39 way points in total, the final bit with top
        significance is only padding. '1111111111111111111111111111111111111110' is a character, who has
        unlocked all waypoints. '111111111 111110000 000 000000000 000000000 0' is a character midway throw act 2."""
        return {
            E_Progression.EP_NORMAL: bytes2bitmap(self.data[643:648])[::-1],
            E_Progression.EP_NIGHTMARE: bytes2bitmap(self.data[667:672])[::-1],
            E_Progression.EP_HELL: bytes2bitmap(self.data[691:696])[::-1]
        }

    @waypoint_map.setter
    def waypoint_map(self, mp: Dict[E_Progression, str]):
        """:param mp: The map needs not to be complete, nor need the strings given be
          complete. Missing values, or values not '0' or '1' will be ignored."""
        current = self.waypoint_map
        haa = self.highest_accessible_act  # type: Dict[E_Progression, int]
        for key in E_Progression.EP_NORMAL, E_Progression.EP_NIGHTMARE, E_Progression.EP_HELL:
            if key not in mp:
                continue
            if key == E_Progression.EP_NORMAL:
                index = [643, 648]
            elif key == E_Progression.EP_NIGHTMARE:
                index = [667, 672]
            elif key == E_Progression.EP_HELL:
                index = [691, 696]
            else:
                continue
            val = mp[key]
            update = current[key]
            for j in range(min(39, len(val))):
                if val[j] in ('0', '1'):
                    update = update[:j] + val[j] + update[(j+1):]
            if update != current[key]:
                self.data = self.data[:index[0]] + bitmap2bytes(update[::-1]) + self.data[index[1]:]
                haa_required = self.get_highest_accessible_act_by_waypoint_bm(update)
                if haa_required > haa[key]:
                    self.highest_accessible_act = {key: haa_required}

    @property
    def progression(self) -> int:
        return self.data[37]

    @progression.setter
    def progression(self, progression: Union[E_Progression, int]):
        """Setter for progression. Set to 5 to enable nightmare. Set to 10 to enable hell."""
        if len(self.data) >= 37:
            self.data = self.data[:37] + int.to_bytes(progression.value if isinstance(progression, E_Progression) else int(progression)) + self.data[38:]

    @property
    def highest_difficulty(self) -> E_Progression:
        """:returns the highest difficulty (normal, nightmare, hell) that is currently open for playing."""
        prog = self.progression
        if prog < 5:
            return E_Progression.EP_NORMAL
        elif prog < 10:
            return E_Progression.EP_NIGHTMARE
        else:
            return E_Progression.EP_HELL

    @staticmethod
    def get_highest_accessible_act_by_waypoint_bm(bm: str) -> int:
        """:param bm: Waypoint bitmap. From left to right 1 signifies open, and 0 closed waypoints.
        :returns, based on bm, what would be the minimum highest accessible act index for reaching all active waypoints?"""
        if len(bm) > 39:
            bm = bm[:39]
        elif len(bm) < 39:
            bm = bm + ((39 - len(bm)) * '0')
        if bm[30:39] != '000000000':
            return 4
        elif bm[27:30] != '000':
            return 3
        elif bm[18:27] != '000000000':
            return 2
        elif bm[9:18] != '000000000':
            return 1
        else:
            return 0

    @property
    def highest_accessible_act(self) -> Dict[E_Progression, int]:
        """Evaluating quest structures for 'has travelled to Act II, III, IV, V'"""
        res = dict()  # type: Dict[E_Progression, int]
        index_hd = self.data.find(b'Woo!', 335)
        for j in range(3):
            val = 0
            # [Note: It appears that the 'Travelled to Act 5 flag' comes right after the three act IV quests.
            #  Also, I interpret 'quest 6 in Act V completed' as 'has won the game'.
            #  So the indices are: Has travelled to Act (II, III, IV, V) and (has won).]
            for base in (index_hd + 14, index_hd + 30, index_hd + 46, index_hd + 56, index_hd + 64):
                index = base + j * 96
                bm = bytes2bitmap(self.data[index:(index+2)])[::-1]
                if bm[0] == '1':
                    val = val + 1
                else:
                    break
            res[E_Progression(j * 5)] = val
        return res

    @highest_accessible_act.setter
    def highest_accessible_act(self, mp: Dict[E_Progression, int]):
        index_hd = self.data.find(b'Woo!', 335)
        for key in mp:
            val = min(mp[key], 5)
            if val < 1:
                continue
            base = index_hd + 10
            if key == E_Progression.EP_NORMAL:
                pass
            elif key == E_Progression.EP_NIGHTMARE:
                base = base + 96
            elif key == E_Progression.EP_HELL:
                base = base + 2 * 96
            else:
                continue
            offsets = (base + 14, base + 30, base + 46, base + 56, base + 64)
            for j in range(min(val, len(offsets))):
                index = offsets[j]
                bm = bytes2bitmap(self.data[index:(index + 2)])[::-1]
                bm = '1' + bm[1:]
                self.data = self.data[:index] + bitmap2bytes(bm[::-1]) + self.data[(index + 2):]

    @property
    def n_cube_contents_shallow(self) -> int:
        """:returns the number of direct items to be found in the Horadric Cube."""
        items = Item(self.data).get_cube_contents()
        c = 0
        for item in items:
            if item.item_parent != E_ItemParent.IP_ITEM:
                c = c + 1
        return c

    @property
    def n_cube_contents_deep(self) -> int:
        """:returns the number of items to be found in the Horadric Cube. Also counting nested items, like socketed runes."""
        return len(Item(self.data).get_cube_contents())

    @property
    def is_demi_god(self) -> bool:
        """Considering that there are 12 points to be had (3 levels of difficulty *4 for Akara, Radagast, and Tyrael)
        and the max level is 99, it is safe to assume, that anyone who has not cheated has no more than 111 hard
        skill points. Allowing for cheats 200 is a natural limit."""
        return sum(self.get_skills()) >= 200

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
            val = self.data[(index_hd + 4):(index_hd + 6)]
            if not as_int:
                return val
            else:
                return int.from_bytes(val, 'little')

    def get_item_count_player(self, as_int = False) -> Union[int, bytes]:
        index_hd = self.data.find(b'JM', 765)
        if index_hd < 0:
            return 0 if as_int else b'\x00\x00'
        else:
            val = self.data[(index_hd + 2):(index_hd + 4)]
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

    def get_rank(self, add_trailing_space_to_non_empty: bool = True) -> str:
        hc = self.is_hardcore()
        prog = self.progression
        ts = ' ' if add_trailing_space_to_non_empty else ''
        if prog < 5:
            return ''
        elif prog < 10:
            return ('Destroyer' if hc else 'Slayer') + ts
        elif prog < 15:
            return ('Conqueror' if hc else 'Champion') + ts
        else:
            return ('Guardian' if hc else ('Matriarch' if self.get_class_enum().is_female() else 'Patriarch')) + ts

    def get_data_mercenary(self) -> Dict[E_Mercenary, int]:
        """Exploratory function. Returns a dict of mercenary personal data."""
        res = dict()  # type: Dict[E_Mercenary, int]
        res[E_Mercenary.IS_DEAD] = int.from_bytes(self.data[177:179], byteorder='little')
        res[E_Mercenary.SEED] = int.from_bytes(self.data[179:183], byteorder='little')
        res[E_Mercenary.ID_NAME] = int.from_bytes(self.data[183:185], byteorder='little')
        res[E_Mercenary.TYPE] = int.from_bytes(self.data[185:187], byteorder='little')
        res[E_Mercenary.EXPERIENCE] = int.from_bytes(self.data[187:191], byteorder='little')
        return res

    @property
    def has_mercenary(self) -> bool:
        """:returns True if and only if the mercenary seed is != 0, which is interpreted as there is a mercenary."""
        return int.from_bytes(self.data[179:183], byteorder='little') != 0

    @property
    def is_dead_mercenary(self) -> bool:
        """:returns True if and only if a mercenary exists at all and is dead. Else False."""
        return int.from_bytes(self.data[177:179], byteorder='little') > 0

    @is_dead_mercenary.setter
    def is_dead_mercenary(self, val: bool):
        val = bool(val)
        self.data = self.data[:177] + int.to_bytes(1 if val else 0, length=2, byteorder='little', signed=False) + self.data[179:]

    def get_info_mercenary(self) -> str:
        """:returns Human-readable mercenary info string."""
        # TODO: So far this format is not fully understood. Improve this function.
        data = self.get_data_mercenary()
        res = f"Raw mercenary info: dead({data[E_Mercenary.IS_DEAD]}), seed({data[E_Mercenary.SEED]}), "\
              f"name({data[E_Mercenary.ID_NAME]}), type({data[E_Mercenary.TYPE]}), exp({data[E_Mercenary.EXPERIENCE]})."
        return res

    def get_name(self, as_str: bool = False) -> Union[bytes, str]:
        """:returns the character name. Either as str or as the 16 byte bytes array."""
        b_name = self.data[20:36]
        return b_name.decode().replace('\x00', '') if as_str else b_name

    def set_name(self, name: str):
        """Sets the given name of maximum length 16.
        DISCLAIMER: THIS FUNCTION DOES NOT SEEM TO WORK. PRODUCES INVALID SAVE-GAMES."""
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
        self.data = self.data[0:20] + bname + self.data[36:]

    def cube_contents_str(self) -> str:
        """:returns human-readable representation of the Horadric Cube's content in short."""
        if not self.has_horadric_cube:
            return ''
        res = 'Cube Content: '
        item_analysis = Item(self.data)
        items = item_analysis.get_cube_contents()
        if len(items) == 0:
            res += "(empty)"
        else:
            res += ", ".join([item.toStringShort() for item in items])
        return res + "\n"

    def _enable_higher_difficulty(self, attr_new: OrderedDict[E_Attributes, int], progression: E_Progression):
        """Code redundancy saving for enable_{nightmare,hell}."""
        if self.progression >= progression.value:
            _log.info(f"{progression} is already enabled. Doing nothing more.")
            return
        self.progression = progression
        attr = self.get_attributes()
        if attr[E_Attributes.AT_LEVEL] >= attr_new[E_Attributes.AT_LEVEL]:
            _log.info(f"Character already is mighty at level {attr[E_Attributes.AT_LEVEL]}. Doing nothing more.")
            return
        old_level = attr[E_Attributes.AT_LEVEL]
        attr[E_Attributes.AT_UNUSED_STATS] = 5 * (attr_new[E_Attributes.AT_LEVEL] - old_level) + (attr[E_Attributes.AT_UNUSED_STATS] if E_Attributes.AT_UNUSED_STATS in attr else 0)
        attr[E_Attributes.AT_UNUSED_SKILLS] = (attr_new[E_Attributes.AT_LEVEL] - old_level) + (attr[E_Attributes.AT_UNUSED_SKILLS] if E_Attributes.AT_UNUSED_SKILLS in attr else 0)
        attr[E_Attributes.AT_LEVEL] = attr_new[E_Attributes.AT_LEVEL]
        attr[E_Attributes.AT_EXPERIENCE] = attr_new[E_Attributes.AT_EXPERIENCE]
        attr[E_Attributes.AT_STASHED_GOLD] = attr_new[E_Attributes.AT_STASHED_GOLD]
        self.set_attributes(attr)

    def enable_nightmare(self):
        # https://classic.battle.net/diablo2exp/basics/levels.shtml
        # https://www.purediablo.com/d2wiki/Gold
        attr_new = odict([(E_Attributes.AT_LEVEL, 38),
                          (E_Attributes.AT_EXPERIENCE, 14641810),
                          (E_Attributes.AT_STASHED_GOLD, 1000000)])
        self._enable_higher_difficulty(attr_new, E_Progression.EP_NIGHTMARE)
        print(f"{self.get_name(True)} is no longer scared by nightmares.")

    def enable_hell(self):
        attr_new = odict([(E_Attributes.AT_LEVEL, 68),
                          (E_Attributes.AT_EXPERIENCE, 250161148),
                          (E_Attributes.AT_STASHED_GOLD, 1750000)])
        self._enable_higher_difficulty(attr_new, E_Progression.EP_HELL)
        print(f"{self.get_name(True)} is prepared to go to hell!")

    def enable_nirvana(self):
        attr_new = odict([(E_Attributes.AT_LEVEL, 86),
                          (E_Attributes.AT_EXPERIENCE, 1196977515),
                          (E_Attributes.AT_STASHED_GOLD, 2200000)])
        self._enable_higher_difficulty(attr_new, E_Progression.EP_MASTER)
        print(f"{self.get_name(True)} has done {'her' if self.get_class_enum().is_female() else 'his'} bit for king and country.")

    def get_class(self, as_str: bool = False) -> Union[bytes, str]:
        """:returns this character's class as a byte or string."""
        val = int(self.data[40])
        if as_str:
            return str(E_Characters(val))
        else:
            return val.to_bytes(1, 'little')

    def get_class_enum(self) -> E_Characters:
        """:returns this character's class as a value of E_Characters."""
        return E_Characters(int.from_bytes(self.get_class(), 'little'))

    def is_dead(self) -> bool:
        """The bit of index 3 in status byte 36 decides if a character is dead."""
        return self.data[36] & 8 > 0

    def set_dead(self, val: bool):
        """Turns the character status to 'dead' or 'alive'. This has nothing to do with the corpse inventory header.
        :param val: If True the character status dead bit will be set. Else it will be cleared."""
        b = self.data[36]
        if val:
            b = b | 8
        else:
            b = b & 247
        self.data = self.data[:36] + int.to_bytes(b, 1) + self.data[37:]

    @staticmethod
    def parse_HMS(val: int) -> Tuple[int, int]:
        """The 21 bit values for Health, Mana and Stamina use a rudimentary floating point mechanic.
        The two leading bits encode the number of quarters to be added.
        :returns a human-readable 2-tuple. The first entry holds the proper value, the second is for quarter points."""
        # Makes a binary of 21 bit out of the value.
        code = '{:0{width}b}'.format(val, width=21)
        main = int(code[0:13], 2)
        quarters = int(code[13:15], 2)
        return main, quarters

    @staticmethod
    def HMS_encode(main: int, quarters: int = 0) -> int:
        """Encodes a pair of values main, and number of quarters into an HMS 21 bit number.
        This is the inverse function of parse_HMS(..)"""
        return (main << 8) + (quarters << 6)

    @staticmethod
    def HMS2str(val: int) -> str:
        main, quarters = Data.parse_HMS(val)
        return f'{main} {quarters}/4' if quarters > 0 else f'{main}'

    def set_attributes(self, vals: OrderedDict[E_Attributes, int]):
        """:param vals: Dictionary with values to be set to the character sheet."""
        sz = 0
        deletees = list()
        for key in vals:
            if vals[key] == 0:
                deletees.append(key)
        for key in deletees:
            del vals[key]
        for key in vals:
            sz = sz + key.get_attr_sz_bits() + 9
        # [Note: Add 9 more bits for the 0x1ff termination sequence. Then round towards next full byte.]
        sz = ceil((sz + 9) / 8.0) * 8
        index = 0
        bitmap = '0' * sz
        for j in range(16):
            key = E_Attributes(j)
            if key not in vals:
                continue
            if vals[key] == 0:
                continue
            if key == E_Attributes.AT_LEVEL:
                # [Note: There is a level in .d2s main header that is used in character selection screen.
                #  It should match the attribute of the same name.]
                self.level_by_header = vals[key]
            bitmap = set_range_to_bitmap(bitmap, index, index + 9, key.value)
            index = index + 9
            bitmap = set_range_to_bitmap(bitmap, index, index + key.get_attr_sz_bits(), vals[key], do_invert=False)
            index = index + key.get_attr_sz_bits()
        bitmap = set_range_to_bitmap(bitmap, index, index + 9, 0x1ff)
        block = bitmap2bytes(bitmap)
        index_start = self.data.find(b'gf', 765) + 2
        index_end_old = self.data.find(b'if', index_start)
        self.data = self.data[0:index_start] + block + self.data[index_end_old:]

    def get_attributes(self) -> OrderedDict[E_Attributes, int]:
        """:returns a dict of all non-zero attribute values."""
        index_start = self.data.find(b'gf', 765) + 2
        if index_start < 0:
            _log.warning("No attributes have been found.")
            return odict()
        res = odict()  # type: OrderedDict[E_Attributes, int]
        c = 0
        index_current = index_start * 8
        while c < 16:
            c = c + 1
            key = get_bitrange_value_from_bytes(self.data, index_current, index_current + 9, do_invert=False)
            if 0 <= key < 16:
                attr = E_Attributes(key)
                res[attr] = get_bitrange_value_from_bytes(self.data,
                                index_current + 9, index_current + 9 + attr.get_attr_sz_bits(), do_invert=False)
                index_current = index_current + 9 + attr.get_attr_sz_bits()
            else:
                if key != 511:
                    _log.warning(f"Unsupported key type {key} encountered.")
                break
        return res

    def get_skills(self) -> List[int]:
        index_start = self.data.find(b'if', 765) + 2
        if index_start < 0:
            _log.warning("No skills have been found.")
            return list()
        # 30 bytes for 30 skills.
        res = list()  # type: List[int]
        for j in range(30):
            res.append(self.data[index_start + j])
        return res

    def set_skills(self, skills: List[int]):
        if len(skills) < 30:
            skills.extend( [0] * (30-len(skills)) )
            _log.warning("Skill list is too short (30 entries are needed). Padding with zeros.")
        block = bytes(skills)
        index_start = self.data.find(b'if', 765) + 2
        index_end = index_start + 30
        self.data = self.data[0:index_start] + block + self.data[index_end:]

    def skills2str(self) -> str:
        """:returns Human-readable representation of the skill set."""
        skills = self.get_skills()
        if len(skills) < 30:
            return 'Skill getter failed.'
        character = self.get_class_enum()
        names = d_skills[character]
        n = len(names)
        res = ''
        for j in range(30):
            res += f"{names[j]}: {skills[j]}, " if j<n else f'{skills[j]}, '
            if (j % 5 == 4) and j < 29:
                res += "\n"
        return res[:-2]

    @property
    def pfname_humanity(self) -> str:
        """Set self.pname_backup to redirect this property from putting the .humanity backup inside the Diablo II directory."""
        pfname = self.pfname
        if self.pname_backup and os.path.isdir(self.pname_backup):
            pfname = os.path.join(self.pname_backup, os.path.basename(pfname))
        return pfname + '.humanity'

    def _update_godmode_backup(self) -> int:
        skills = self.get_skills()
        if self.is_demi_god:
            _log.warning("God mode seems to be active already. Cannot backup the gods!")
            return 1
        attr = self.get_attributes()
        keys = list(d_god_attr.keys())
        # Backup data structure following keys in d_god_attr.
        bu_attr = list()  # type: List[int]
        for key in keys:
            bu_attr.append(attr[key] if key in attr else 0)
        a = b''
        # [Note: Since I am making up my own section of save game code I take the luxury of 16 bits per attr und 8 bit per skill.]
        for val in [int.to_bytes(x,3,'little') for x in bu_attr]:
            a += val
        backup = a + bytes(skills)
        with open(expanduser(self.pfname_humanity), 'wb') as OUT:
            OUT.write(backup)
            print(f"Wrote humanity backup '{self.pfname_humanity}' for {self.get_name(True)}.")
        return 0

    def _restore_godmode_backup(self) -> int:
        if not os.path.isfile(self.pfname_humanity):
            _log.warning(f"Unable to restore humanity to {self.get_name(True)}. Backup file '{self.pfname_humanity}' was not found.")
            return 1
        with open(self.pfname_humanity, 'rb') as IN:
            backup = IN.read()
        attrs_restored = odict()  # type: Dict[E_Attributes, int]
        keys = list(d_god_attr.keys())
        for j in range(len(keys)):
            attrs_restored[keys[j]] = int.from_bytes(backup[(j*3):((j+1)*3)], 'little')

        skills_human = list()
        for j in range(30):
            skills_human.append(backup[len(keys) * 3 + j])
        current_attrs = self.get_attributes()
        current_unused_skills = current_attrs[E_Attributes.AT_UNUSED_SKILLS] if E_Attributes.AT_UNUSED_SKILLS in current_attrs else 0
        sum_attr = 0
        for key in [E_Attributes.AT_STRENGTH, E_Attributes.AT_ENERGY, E_Attributes.AT_DEXTERITY, E_Attributes.AT_VITALITY, E_Attributes.AT_UNUSED_STATS]:
            if key in current_attrs:
                sum_attr += current_attrs[key]
        for key in attrs_restored:
            current_attrs[key] = attrs_restored[key]
        # Preserve skill and stat level points that have been earned in god mode.
        attr_delta = sum_attr - sum_god_attr
        skill_delta = sum(self.get_skills()) + current_unused_skills - sum_god_skills
        current_attrs[E_Attributes.AT_UNUSED_STATS] += attr_delta
        current_attrs[E_Attributes.AT_UNUSED_SKILLS] += skill_delta
        self.set_attributes(current_attrs)
        self.set_skills(skills_human)
        return 0

    def enable_godmode(self):
        if self.is_demi_god:
            return
        attrs = self.get_attributes()
        for key in d_god_attr:
            attrs[key] = d_god_attr[key]
        self._update_godmode_backup()
        self.set_attributes(attrs)
        self.set_skills(d_god_skills)

    def disable_godmode(self) -> int:
        if not self.is_demi_god:
            return 0  # << This is no crime.
        err = self._restore_godmode_backup()
        if err:
            return 1
        index_start = self.data.find(b'mf', 765 + 32)
        if index_start < 0:
            return 2
        self.data = self.data[0:index_start]
        return 0

    def is_hardcore(self) -> bool:
        """The bit of index 2 in status byte 36  decides if a character is hardcore."""
        return self.data[36] & 4 > 0

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

    def drop_items(self, items: List[Item]):
        """Dropping multiple items at once is dangerous due to indices becoming obsolete. This function hides this danger."""
        items.sort(key=lambda x: x.index_start, reverse=True)
        for item in items:
            self.drop_item(item)

    @staticmethod
    def count_main_items(bts: bytes) -> int:
        """:returns the number of items in bts that are not marked parent 'E_ItemParent.IP_ITEM'.
        I.e., counting items that also count in .d2s file item counters."""
        bts = re.sub(b'^.*?JM', b'JM', bts)
        candidates = bts.split(b'JM')  # type: List[bytes]
        candidates = [(b'JM' + cand) for cand in candidates]
        c = 0
        for candidate in candidates:
            # [Note: Countable items have >6 bytes. >>6 actually.]
            if len(candidate) <= 6:
                continue
            item = Item(candidate, 0, len(candidate))
            if item.item_parent != E_ItemParent.IP_ITEM:
                c = c + 1
        return c

    def get_storage_occupation_maps(self, storage: E_ItemStorage) -> str:
        """:returns for the selected ItemStorage a line-wise (row major) bitmap string. Each number stands
        for a slot in the respective storage type (cube, stash, inventory). '0' says: free slot,
        '1' says: slot is occupied by some item.
        The Horadric Cube is 4x3. The Stash is 8x6. The inventory is 4x10."""
        size = storage.size
        n_y = size[0]
        n_x = size[1]
        n = n_x * n_y
        if not n:
            return ''
        bm = '0' * n
        item_analysis = Item(self.data)
        items = item_analysis.get_block_items(E_ItemBlock.IB_PLAYER)
        for item in items:
            if item.stash_type != storage or item.item_parent != E_ItemParent.IP_STORED:
                continue
            vol = item.volume
            if item.volume is None:
                continue
            y = item.row
            x = item.col
            for j in range(vol[0]):
                for k in range(vol[1]):
                    index = (j+y) * n_x + (k+x)
                    bm = bm[:index] + '1' + bm[(index+1):]
        return bm

    def add_items_to_player(self, items: bytes):
        """Warning: Be sure to add multiple items in a sensible order!
        :param items: Byte string of JM...-items."""
        # [Note: For backwards-compatibility. Delete all bytes prior to the first b'JM'.]
        items = re.sub(b'^.*?JM', b'JM', items)
        count = self.count_main_items(items)
        index_start = Item(self.data).get_block_index()[E_ItemBlock.IB_PLAYER][0]
        self.data = self.data[0:index_start] + items + self.data[index_start:]
        self.set_item_count(E_ItemBlock.IB_PLAYER_HD, self.get_item_count_player(True) + count)
        # print(f"Attempting to add {count} new items to the player's inventory.")

    def find_space_for_item(self, item: Item, storage: E_ItemStorage, smap: Optional[str] = None) -> Optional[Tuple[int,int]]:
        """:returns the coordinates of the top left corner for the item where it would fit."""
        if not smap:
            smap = self.get_storage_occupation_maps(storage)
        volume = item.volume
        if any([x is None for x in [smap, volume]]):
            return None
        n_y = storage.size[0] - volume[0] + 1
        n_x = storage.size[1] - volume[1] + 1
        for pos_x in range(n_x):
            for pos_y in range(n_y):
                position_is_good = True
                for j in range(volume[0]):
                    for k in range(volume[1]):
                        if smap[storage.size[1] * (pos_y+j) + (pos_x+k)] == '1':
                            position_is_good = False
                            break
                    if not position_is_good:
                        break
                if position_is_good:
                    return pos_y, pos_x
        return None

    def place_items_into_storage_maps(self, items: List[Item], storage: Optional[Union[E_ItemStorage, List[E_ItemStorage]]] = None) -> List[Item]:
        """Places the given items into storage. Scanning for free space. Correcting item count.
        :param items: Items to be placed. May also be socketed items.
        :param storage: Storage targets. If None all targets will be tried in order cube, stash, inventory.
        :returns remaining items that could not be placed. Empty list in case of complete success."""
        # > Preliminaries. -------------------------------------------
        if not items:
            return []  #<< Nothing to do.
        if storage is None:
            storage = [E_ItemStorage.IS_CUBE, E_ItemStorage.IS_STASH, E_ItemStorage.IS_INVENTORY]
        if isinstance(storage, list):
            for st in storage:
                items = self.place_items_into_storage_maps(items, st)
            return items
        # < ----------------------------------------------------------
        res = list()  # type: List[Item]
        bts = b''
        am_in_sockets = False
        for item in items:
            if isinstance(item, bytes):
                item = Item(item, 0, len(item))
            if item.item_parent == E_ItemParent.IP_ITEM:
                if am_in_sockets:
                    # Add those bts to the currently active parent item.
                    bts += item.data_item
                else:
                    res.append(item)
            else:
                am_in_sockets = False
                coords = self.find_space_for_item(item, storage)
                if (coords is None) or (item.type_code == 'box' and storage == E_ItemStorage.IS_CUBE):
                    # ^Cannot place the Horadric Cube into the Horadric Cube.
                    res.append(item)
                else:
                    item.row = coords[0]
                    item.col = coords[1]
                    item.stash_type = storage
                    item.item_parent = E_ItemParent.IP_STORED
                    bts = item.data_item
                    if item.n_sockets_occupied:
                        am_in_sockets = True
                    else:
                        self.add_items_to_player(bts)
                        bts = b''
        if bts:
            self.add_items_to_player(bts)
        return res

    @staticmethod
    def _normalize_rune_item(item: Item) -> bytes:
        """Dispels magic (dropping mod section), removes runeword-powers (not the runes though),
        use self.separate_socketed_items_from_item for that and sets the quality to normal."""
        bmr = bytes2bitmap(item.copy_with_item_property_set(E_ItemBitProperties.IP_RUNEWORD, False))[::-1]
        quality = item.quality
        if quality not in (E_Quality.EQ_NORMAL, E_Quality.EQ_SUPERIOR) or 8 * len(bmr) < 154 or item.n_sockets == 0:
            return item.data_item  # << Nothing to do.
        bmr_mods_superior = ''
        if quality == E_Quality.EQ_SUPERIOR:
            d_mods_superior = item.get_known_mods(is_mod_superior_weapon=item.is_weapon, is_mod_superior_armor=item.is_armor)
            for j in range(len(d_mods_superior)):
                bmr_mods_superior += d_mods_superior[j]['bmr']
        ext_index = item.get_extended_item_index()
        # [Drops all mods. The '1111111110*' suffix, too.]
        bmr = bmr[:ext_index[E_ExtProperty.EP_MODS][0]]
        bmr = bmr[:ext_index[E_ExtProperty.EP_RUNEWORD][0]] + bmr[ext_index[E_ExtProperty.EP_RUNEWORD][1]:]
        #bmr = bmr[:ext_index[E_ExtProperty.EP_QUEST_SOCKETS][0]] + '000' + bmr[ext_index[E_ExtProperty.EP_QUEST_SOCKETS][1]:]
        bmr += bmr_mods_superior
        bmr += '111111111'
        bm = prefix_bitmap_to_8_product(bmr[::-1])
        return bitmap2bytes(bm)

    def separate_socketed_items_from_item(self, item: Item):
        """Will remove socketed items from the given item and put them into the player's inventory.
        Preferably close to that item, else into the cube, stash, or backpack inventory.
        :param item: A socketed item that has items socketed into it."""
        if item is None or not item.n_sockets:
            return
        new_items = list()  # type: List[Union[Item, bytes]]
        target_inventories = [E_ItemStorage.IS_CUBE, E_ItemStorage.IS_STASH, E_ItemStorage.IS_INVENTORY]
        if item.stash_type in target_inventories:
            target_inventories = list(filter(lambda x: x != item.stash_type, target_inventories))
            target_inventories.insert(0, item.stash_type)
        former_child = item
        while True:
            child = former_child.get_next_item()
            if child.item_parent != E_ItemParent.IP_ITEM:
                break
            former_child = child
            new_items.append(child)
        # [Note: Fragile code here. It is important to delete the items in reverse order, so that the
        #  internal indices of the yet un-handled Item objects in the list remain intact.
        #  It is also important to set move the parent property IP_ITEM to IP_STORED only after removal, so that
        #  the main item count stays intact during the call to drop_item(..).]
        for j in reversed(range(len(new_items))):
            self.drop_item(new_items[j])
            new_items[j].item_parent = E_ItemParent.IP_STORED
        self.drop_item(item)
        item.n_sockets_occupied = 0
        if item.get_item_property(E_ItemBitProperties.IP_RUNEWORD):
            new_items.insert(0, self._normalize_rune_item(item))
        else:
            new_items.insert(0, item.data_item)
        self.place_items_into_storage_maps(new_items, target_inventories)

    def set_sockets(self, item, count: int):
        """Will set or remove sockets. Won't delete so many sockets that existing items
        would hang in the air.
        :param item: Target socketable item. Its byte code will be altered in this
          data.data. Note that this may invalidate any index_start and index_end
          in existing Item objects. Consider refreshing these.
        :param count: How many sockets? 6 is the absolute maximum. Note, that the
          game actually will ensure that this is capped by whatever the item supports.
          This may be thanks to the Larzuk mechanic."""
        if item.is_analytical:
            return
        if item.get_item_property(E_ItemBitProperties.IP_RUNEWORD):
            _log.info(f"Unable to alter socket count of {item.type_name} to {count} due to runeword magic.")
            return
        if item.item_class == E_ItemClass.IC_QUEST_ITEMS:
            _log.info(f"Unable to alter socket count of {item.type_name} to {count} due to it being a quest item.")
            return
        quality = item.quality
        # Magically enhanced items may have 0-4, other magical items may have 0-1 sockets. Enforce that rule.
        # Src: https://diablo2.diablowiki.net/Sockets
        if quality == E_Quality.EQ_MAGICALLY_ENHANCED:
            if count > 4:
                count = 4
        elif quality in (E_Quality.EQ_RARE, E_Quality.EQ_SET, E_Quality.EQ_UNIQUE, E_Quality.EQ_CRAFT):
            if count > 1:
                count = 1
        if count > (item.volume[0] * item.volume[1]):
            count = (item.volume[0] * item.volume[1])
        if count < 0:
            count = 0
        if (not item.is_socketable) or item.get_item_property(E_ItemBitProperties.IP_COMPACT):
            return
        ext_index = item.get_extended_item_index()
        n_occupied = item.get_extended_item_int_value(E_ExtProperty.EP_QUEST_SOCKETS)
        if count < n_occupied:
            _log.info(f"Unable to reduce socket count of {item.type_name} to {count}. there are {n_occupied} sockets that are already occupied.")
            count = n_occupied
        if item.n_sockets == count:
            return  # << Nothing to do.
        index_sockets = ext_index[E_ExtProperty.EP_SOCKETS]
        _log.info(f"Attempting to set {count} sockets to item {item.type_name}.")
        if item.n_sockets:
            if count > 0:
                # Set socket count to new value.
                bts = set_bitrange_value_to_bytes(item.data_item, index_sockets[0], index_sockets[1], count)
                bmr = bytes2bitmap(bts)[::-1]
                bmr = bmr[:index_sockets[0]] + '{:0{width}b}'.format(count,width=4)[::-1] + bmr[index_sockets[1]:]
            else:
                # Remove all sockets.
                bts = item.copy_with_item_property_set(E_ItemBitProperties.IP_SOCKETED, False)
                bmr = bytes2bitmap(bts)[::-1]
                bmr = bmr[:index_sockets[0]] + bmr[index_sockets[1]:]
                index_quest_sockets = ext_index[E_ExtProperty.EP_QUEST_SOCKETS]
                # [Note: For non-quest items this number counts the number of employed sockets.]
                bmr = bmr[:index_quest_sockets[0]] + '000' + bmr[index_quest_sockets[1]:]
        else:
            # Create sockets ex nihilo.
            bts = item.copy_with_item_property_set(E_ItemBitProperties.IP_SOCKETED, True)
            bmr = bytes2bitmap(bts)[::-1]
            bmr = bmr[:index_sockets[0]] + '{:0{width}b}'.format(count,width=4)[::-1] + bmr[index_sockets[1]:]
        bmr = re.sub('0+$', "", bmr)
        if len(bmr) % 8:
            bmr += '0' * (8 - len(bmr) % 8)
        bts = bitmap2bytes(bmr[::-1])
        self.data = self.data[:item.index_start] + bts + self.data[item.index_end:]

    def dispel_magic(self, item):
        """Dispels magic on rare, crafted, magic, set and unique items."""
        if item.is_analytical or not item.is_magic:
            return
        is_charm = item.is_charm
        index_ext = item.get_extended_item_index()
        if item.n_sockets_occupied:
            _log.warning(f"Item {item.type_name} has {item.n_sockets_occupied} occupied sockets. Cannot dispel its magic without removing stones and runes first.")
            return

        # First set quality to normal (2) formally.
        bmr = bytes2bitmap(item.data_item)[::-1]
        bmr = bmr[:150] + '0100' + bmr[154:]

        # Handle Sockets (mechanical items).
        id_qs = index_ext[E_ExtProperty.EP_QUEST_SOCKETS]
        bmr = bmr[:id_qs[0]] + ('0' * (id_qs[1]-id_qs[0])) + bmr[id_qs[1]:]

        bmr = bmr[:index_ext[E_ExtProperty.EP_MODS][0]] + '111111111'
        bmr = bmr[:index_ext[E_ExtProperty.EP_SET][0]] + bmr[index_ext[E_ExtProperty.EP_SET][1]:]
        bmr = bmr[:index_ext[E_ExtProperty.EP_QUALITY_ATTRIBUTES][0]] + ('0'*12 if is_charm else '') + bmr[index_ext[E_ExtProperty.EP_QUALITY_ATTRIBUTES][1]:]

        bm = bmr[::-1]
        bm = prefix_bitmap_to_8_product(bm)

        bts = bitmap2bytes(bm)
        self.data = self.data[:item.index_start] + bts + self.data[item.index_end:]
        _log.info(f"Dispelled magic for {item.type_name}.")

    def set_ethereal(self, item: Item, enable: Optional[bool] = None):
        if item.is_analytical or item.get_item_property(E_ItemBitProperties.IP_COMPACT):
            return
        if enable is None:
            enable = not item.get_item_property(E_ItemBitProperties.IP_ETHEREAL)
        if item.get_item_property(E_ItemBitProperties.IP_ETHEREAL) == enable:
            return  # << Nothing to do.
        item.is_ethereal = enable
        self.data = self.data[:item.index_start] + item.data_item + self.data[item.index_end:]
        print(f"Attempting to set item '{item.type_name}' to {'' if enable else 'not '}ethereal.")

    def jewelize(self, item: Item, *, do_replace=True, tpl: E_ItemTpl = E_ItemTpl.IT_JEWEL) -> Optional[Item]:
        """Will verify if the given item has intrinsic magic power. If so, clone that power into a jewel.
        :param item: Target item.
        :param do_replace: Should the original item be replaced by the new jewel?
        :param tpl: Template to be used as base for the new item.
        :returns the created magic jewel."""
        index_ext = item.get_extended_item_index()
        if index_ext is None:
            return

        bts_tpl = d_data_tpl[tpl] if tpl in d_data_tpl else d_data_tpl[E_ItemTpl.IT_JEWEL]
        item_tpl = Item(bts_tpl, 0, len(bts_tpl))
        type_code_tpl = item_tpl.type_code
        # [Note: So far runeword extended indexing only works reliably for normal and superior items.]
        has_runeword = item.get_item_property(E_ItemBitProperties.IP_RUNEWORD) and \
                       item.quality in (E_Quality.EQ_NORMAL, E_Quality.EQ_SUPERIOR, E_Quality.EQ_INFERIOR)

        # [Note: Querying n_sockets is relevant. The technique does not work for mechanic items.
        #  While, e.g., a mechanic ring can be created, the game does not allow to socket into it.]
        if (not has_runeword) and (item.type_code.lower() == type_code_tpl or item.n_sockets > 0 or
                item.quality not in (E_Quality.EQ_RARE, E_Quality.EQ_MAGICALLY_ENHANCED, E_Quality.EQ_CRAFT, E_Quality.EQ_UNIQUE, E_Quality.EQ_SET)):
            return None

        bmr_item = bytes2bitmap(item.data_item)[::-1]
        index_item_magic = index_ext[E_ExtProperty.EP_MODS_RUNEWORD if has_runeword else E_ExtProperty.EP_MODS]
        bmr_magic = bmr_item[index_item_magic[0]:index_item_magic[1]]
        if len(bmr_magic) == 0:
            return
        bmr_magic += '111111111'

        # Muggle jewel, the extension part [160:] merely comprised the 0x1ff part anyway.
        bmr_tpl = bytes2bitmap(bts_tpl)[::-1]
        bmr_tpl = bmr_tpl[0:160]
        bmr_tpl += bmr_magic

        # Copy quality and insert the quality attributes behind the class specific data.
        index_quality = index_ext[E_ExtProperty.EP_QUALITY]
        if has_runeword or item.quality in (E_Quality.EQ_UNIQUE, E_Quality.EQ_SET):
            bmr_quality = '0010'  #<< Magically Enhanced.
            bmr_quality_attributes = '0' * 22  #<< Prefix and Suffix code 0,0 just means 'empty'.
        else:
            index_qa = index_ext[E_ExtProperty.EP_QUALITY_ATTRIBUTES]
            bmr_quality = bmr_item[index_quality[0]:index_quality[1]]
            bmr_quality_attributes = bmr_item[index_qa[0]:index_qa[1]]
        # [Note: Quality is always at the same site, and always of length 4. So the next line is fine.]
        bmr_tpl = bmr_tpl[:index_quality[0]] + bmr_quality + bmr_tpl[index_quality[1]:]
        # [Note: The muggle jewel is normal. Its original quality attributes are emtpy.]
        # [Note: Only the realm bit is following. Inserting the item's quality attributes.]
        bmr_tpl = bmr_tpl[:159] + bmr_quality_attributes + bmr_tpl[159:]
        bm_tpl = prefix_bitmap_to_8_product(bmr_tpl[::-1])

        item_forged = Item(bitmap2bytes(bm_tpl), 0, len(bm_tpl) // 8)
        item_forged.item_level = item.item_level
        if do_replace:
            for item_part in reversed(item.get_item_dismantled()):
                self.drop_item(item_part)
        self.place_items_into_storage_maps([item_forged], E_ItemStorage.IS_CUBE)
        return item_forged

    def regrade(self, item, grade: Optional[E_ItemGrade] = None):
        """Upgrade or downgrade the given item along the lines of normal, exceptional, elite, post-elite."""
        if item.is_analytical or (grade is not None and grade.value not in (0,1,2,3)):
            return
        type_code_old = item.type_code
        fam = ItemFamily.get_family_by_code(type_code_old)
        gval_old = (ItemFamily.get_grade_for_code(type_code_old) if grade is None else grade).value
        if not isinstance(gval_old, int):
            _log.warning("Weird Grade enum value encountered.")
            return
        if fam is None:
            return
        keys = fam.code_names.keys()
        if not keys or len(keys) < 2:
            return  # << Nothing to do.
        gval_new = (gval_old + 1) % len(keys)
        try:
            type_code_new = list(keys)[gval_new]
        except ValueError:
            return
        if item.n_sockets_occupied is not None and item.n_sockets_occupied > 0:
            if gval_new < gval_old:
                _log.warning(f"Unable to downgrade item '{item.type_name}' with {item.n_sockets_occupied} occupied sockets.")
                return
            elif item.get_item_property(E_ItemBitProperties.IP_RUNEWORD):
                # [Note: This is legit, but we have to ensure that the number of sockets will not increase during upgrade.]
                index_sock = item.get_extended_item_index()[E_ExtProperty.EP_SOCKETS]
                if index_sock[1] - index_sock[0] != 4:
                    _log.warning(f"Failure to adjust socket count of {item.n_sockets} to {item.n_sockets_occupied}. Strange socket index block of len != 4: {index_sock}.")
                    return
                bmr_sock = '{:0{width}b}'.format(item.n_sockets_occupied, width=4)[::-1]
                bmr = bytes2bitmap(item.data_item)[::-1]
                bmr = bmr[:index_sock[0]] + bmr_sock + bmr[index_sock[1]:]
                item.data_item = bitmap2bytes(bmr[::-1])

        name_old = item.type_name
        item.type_code = type_code_new
        was_ethereal = False
        if item.is_ethereal:
            item.is_ethereal = False
            was_ethereal = True
        item.durability2default()
        # Ensure that a good normal item will be a good exceptional item, will be a good elite item.
        p = 0.5
        ac = item.defense
        if ac and ac > 0 and type_code_old in d_armor_weapons:
            dur, ac_min, ac_max = d_armor_weapons[type_code_old]
            if ac_max > ac_min:
                p = (ac - ac_min) / (ac_max - ac_min)
        item.defense2default(p)
        if item.item_level is not None:
            ilevel = 32 * (gval_new - gval_old) + item.item_level
            if ilevel < 0:
                ilevel = 0
            elif ilevel > 99:
                ilevel = 99
            item.item_level = ilevel
        if was_ethereal:
            item.is_ethereal = True

        _log.info(f"Attempting to create {item.item_grade} {item.type_name} from {name_old}.")
        self.data = self.data[:item.index_start] + item.data_item + self.data[item.index_end:]

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """:return Time string aiming to become part of a backup pfname."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def save2disk(self, pfname: str = None, prefix_timestamp: bool = False):
        """:param pfname: Target pfname. If not given, will use the original pfname, overwriting the original file.
        :param prefix_timestamp: If False, no effect. If True, the fname wil lbe prefixed with a timestamp
          and suffixed with '.backup'.
        Write this data structure's current state to disk. As is. E.g., no checksums are updated automatically."""
        if pfname is None:
            pfname = self.pfname
        if prefix_timestamp:
            parts = os.path.split(pfname)
            pname = parts[0]
            fname = parts[1]
            fname = re.sub(regexp_invalid_pfname_chars, '_', fname)
            pfname = os.path.join(pname, Data.get_time() + '_' + fname + '.backup')
        with open(expanduser(pfname), 'wb') as OUT:
            OUT.write(self.data)
        print(f"Wrote {self.get_class(True)} {self.get_name(True)} to disk: {pfname}")

    def __str__(self) -> str:
        core = 'hardcore' if self.is_hardcore() else 'softcore'
        cube_posessing = 'owning' if self.has_horadric_cube else 'lacking'
        golem = 'golem commanding, ' if self.has_iron_golem else ''
        merc = self.get_info_mercenary()
        god_status = ('demi-goddess' if self.is_demi_god else 'heroine') if self.get_class_enum().is_female() else ('demi-god' if self.is_demi_god else 'hero')
        attr = self.get_attributes()
        s_attr = ''
        for key in self.get_attributes():
            s_attr += f"{key.name}: {self.HMS2str(attr[key])},\n" if key.get_attr_sz_bits() == 21 else f"{key.name}: {attr[key]},\n"
        msg = f"{self.get_rank()}{self.get_name(True)} ({self.pfname}), a Horadric Cube (holding {self.n_cube_contents_shallow} items) {cube_posessing}, {golem}"\
              f"level {attr[E_Attributes.AT_LEVEL]} (hd: {self.level_by_header}/prog: {self.progression}) {core} {self.get_class(True)} {god_status}.\n"\
              f"merc: {merc}\n"\
              f"{self.cube_contents_str()}"\
              f"Checksum (current): '{int.from_bytes(self.get_checksum(), 'little')}', "\
              f"Checksum (computed): '{int.from_bytes(self.compute_checksum(), 'little')}', "\
              f"file version: {self.get_file_version()}, file size: {len(self.data)}, file size in file: {self.get_file_size()}, \n" \
              f"direct player item count: {self.get_item_count_player(True)}, is dead: {self.is_dead()}, direct mercenary item count: {self.get_item_count_mercenary(True)}, \n" \
              f"Progress: {self.progression}.\n" \
              f"attributes: {s_attr}" \
              f"learned skill-set : {self.skills2str()}\n" \
              f"quest map: {self.get_quests_simplified()}\n" \
              f"waypoint map: {self.waypoint_map}\n" \
              f"acts completed: {self.highest_accessible_act}"
        item_analysis = Item(self.data)
        items = item_analysis.get_block_items()
        for item in items:
            msg += f"\n{item}"
            if not item.item_block.is_header:
                msg += "\n"
        msg += "\nStorage Occupation:\n"
        for storage in [E_ItemStorage.IS_CUBE, E_ItemStorage.IS_STASH, E_ItemStorage.IS_INVENTORY]:
            bm = self.get_storage_occupation_maps(storage)
            n_x = storage.size[1]
            msg += f"{storage}:\n"
            for j in range(storage.size[0]):
                msg += bm[j*n_x:(j+1)*n_x] + "\n"
        return msg


class Horadric:
    def __init__(self, args: Optional[List[str]] = None):
        if not self.is_standalone:
            self.data_all = list()  # type: List[Data]
            return
        # > Setting up the data. -------------------------------------
        parsed = self.parse_arguments(args)
        pfnames_in = parsed.pfnames if parsed.pfnames else list()  # type: List[str]
        self.data_all = [Data(pfname) for pfname in pfnames_in]
        #< -----------------------------------------------------------
        #> Backups. --------------------------------------------------
        do_backup = not parsed.omit_backup  # type: bool
        if do_backup:
            self.backup(parsed.pfname_backup)
        else:
            print("Omitting backups.")
        # < ----------------------------------------------------------
        if parsed.info:
            print(self.get_info())

        if parsed.softcore and parsed.hardcore:
            print("Both, set to hardcore and set to softcore has been requested. Ignoring both.")
        elif parsed.softcore or parsed.hardcore:
            self.set_hardcore(parsed.hardcore)

        if parsed.revive_self:
            self.set_dead_self(False)

        if parsed.revive_merc:
            self.set_dead_mercenary(False)

        if parsed.redeem_golem:
            for data in self.data_all:
                self.redeem_golem(data)

        if parsed.drop_horadric:
            for data in self.data_all:
                self.drop_horadric(data)

        if parsed.save_horadric:
            if len(pfnames_in) == 1:
                self.save_horadric(parsed.save_horadric)
            else:
                _log.warning("Saving of Horadric Cube content requires 1 target character exactly.")

        if parsed.empty_sockets_horadric:
            for data in self.data_all:
                self.empty_sockets_horadric(data)

        if isinstance(parsed.set_sockets_horadric, int):
            for data in self.data_all:
                self.set_sockets_horadric(data, parsed.set_sockets_horadric)

        if parsed.dispel_magic:
            for data in self.data_all:
                self.dispel_magic_horadric(data)

        if parsed.toggle_ethereal:
            for data in self.data_all:
                self.toggle_ethereal(data)

        if parsed.jewelize:
            for data in self.data_all:
                tpl = E_ItemTpl.IT_JEWEL
                if parsed.jewelize.upper == 'rin':
                    tpl = E_ItemTpl.IT_RING
                elif parsed.jewelize.upper == 'cm1':
                    tpl = E_ItemTpl.IT_CHARM
                elif parsed.jewelize.upper == 'amu':
                    tpl = E_ItemTpl.IT_AMULET
                self.jewelize_horadric(data, tpl)

        if parsed.set_waypoints:
            self.set_waypoints(parsed.set_waypoints)

        if parsed.set_quests:
            self.set_quests(parsed.set_quests)

        if parsed.ensure_horadric:
            for data in self.data_all:
                self.ensure_horadric(data)

        if parsed.regrade_horadric:
            for data in self.data_all:
                self.regrade_horadric(data)

        if parsed.create_rune_cube is not None:
            self.create_rune_cube(parsed.create_rune_cube)

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

        if parsed.boost_attributes is not None:
            self.boost(E_Attributes.AT_UNUSED_STATS, parsed.boost_attributes)

        if parsed.boost_skills is not None:
            self.boost(E_Attributes.AT_UNUSED_SKILLS, parsed.boost_skills)

        if parsed.reset_attributes:
            self.reset_attributes()

        if parsed.reset_skills:
            self.reset_skills()

        if parsed.enable_nightmare:
            self.enable_nightmare()

        if parsed.enable_hell:
            self.enable_hell()

        if parsed.enable_nirvana:
            self.enable_nirvana()

        if parsed.enable_godmode:
            self.enable_godmode()

        if parsed.disable_godmode:
            self.disable_godmode()

        if parsed.info_stats:
            self.info_stats()

    @property
    def is_standalone(self) -> bool:
        """Is this script running on its own, or does it serve the Horadric Exchange GUI?
        The greatest effect of this is that a non-standalone script will not autoupdate and autosave."""
        return __name__ == "__main__"

    def get_data_by_pfname(self, pfname: str, *, create_if_missing: bool = False) -> Optional[Data]:
        """:returns the data block with the given pfname. Or None, in case of failure."""
        for data in self.data_all:
            if data.pfname == pfname:
                return data
        if create_if_missing:
            if not Path(pfname).is_file():
                _log.warning(f"Target file '{pfname}' not found.")
                return None
            data = Data(pfname)
            self.data_all.append(data)
            return data
        return None

    def info_stats(self):
        for data in self.data_all:
            # [Note: Attributes live in the 'gf'-section. Beyond, 'if' will start the skills section.]
            index_start = data.data.find(b'gf', 765)
            index_end = data.data.find(b'if', index_start)
            bts = data.data[index_start:index_end]
            bmr = bytes2bitmap(bts)[::-1]
            print(f"{data.get_name(True)} from '{data.pfname}'.")
            print("Bitmap (little endian):")
            print(bmr)
            print(f"Byte Stream [{index_start}:{index_end}]:")
            print(bts.hex(' '))
            print("Decoded (little endian):")
            # Ignore the first 2 bytes. They are the 'gf' prefix.
            index = 16
            for j in range(16):
                key = bmr[index:(index+9)]
                if not key:
                    break
                val_key = get_range_from_bitmap(key[::-1], 0, len(key))
                # Attribute keys range in 0,..,15. A 'key' > 15 is bound to be the 0x1ff section terminator.
                if val_key > 15:
                    print(f"Remainder: {bmr[index:]}")
                    break
                attr = E_Attributes(val_key)
                index_end = index + 9 + attr.get_attr_sz_bits()
                raw = bmr[index:index_end]
                print(f"Attr-ID: {key} ({attr.name}, {val_key}), Storage size: {attr.get_attr_sz_bits()}, bit range: [{index}:{index_end}]")
                twenty_one_bit_ignore_bits = 8 if attr.get_attr_sz_bits() == 21 else 0
                part0 = bmr[(index+9):(index+9+twenty_one_bit_ignore_bits)]
                part1 = bmr[(index+9+twenty_one_bit_ignore_bits):index_end]
                code_quarters = get_range_from_bitmap(part0[::-1], 0, len(part0)) if len(part0) else 0
                quarters = 0
                if code_quarters == 64:
                    quarters = 1
                elif code_quarters == 128:
                    quarters = 2
                elif code_quarters == 192:
                    quarters = 3
                index = index_end
                s_prefix = f"{part0} ({get_range_from_bitmap(part0[::-1], 0, len(part0))} -> {quarters}/4)" if part0 else ""
                s_suffix = f"{part1} ({get_range_from_bitmap(part1[::-1], 0, len(part1))})"
                print(f"Val: {s_prefix} {s_suffix}\nraw: {raw}\n")
            print("------------------------------------------------------------------------------")

    def backup(self, pfname_backup: Optional[str] = None):
        for data in self.data_all:
            pfname_b = ''
            if pfname_backup:
                pfname_b = pfname_backup
                if len(self.data_all) > 1:
                    pfname_b += data.get_name(True) + '_' + pfname_b
            else:
                pfname_b += data.get_name(True)
            data.save2disk(pfname_b, prefix_timestamp=pfname_backup is None)

    def get_info(self) -> str:
        """Print various info to all files to the console."""
        n = len(self.data_all)
        res = ""
        for j in range(n):
            res += str(self.data_all[j])
            if j < (n-1):
                res += "\n====================\n"
        return res

    def set_hardcore(self, hardcore: bool):
        for data in self.data_all:
            data.set_hardcore(hardcore)
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def set_dead_self(self, val: bool):
        for data in self.data_all:
            print(f"Attempting to ensure {'death' if val else 'life'} for {data.get_name(True)}.")
            data.set_dead(val)
            if not val:
                attrs = data.get_attributes()
                if E_Attributes.AT_MAX_HP in attrs:
                    print(f"Attempting to heal {data.get_name(True)}'s wounds, too.")
                    attrs[E_Attributes.AT_CURRENT_HP] = attrs[E_Attributes.AT_MAX_HP]
                    data.set_attributes(attrs)
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def set_dead_mercenary(self, val: bool):
        for data in self.data_all:
            print(f"Attempting to ensure {'death' if val else 'life'} for {data.get_name(True)}'s mercenary.")
            data.is_dead_mercenary = val
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def boost(self, attr: E_Attributes, val: int):
        """Sets the target attribute to the given val."""
        for data in self.data_all:
            print(f"Attempting to boost '{attr.name}' to the value of {val}")
            attributes = data.get_attributes()
            if val:
                attributes[attr] = val
            else:
                del attributes[attr]
            data.set_attributes(attributes)
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    @staticmethod
    def _subtract_and_encode_quarter_tuples(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        main = a[0] - b[0]
        quarters = a[1] - b[1]
        if quarters < 0:
            quarters += 4
            main -= 1
        return Data.HMS_encode(main, quarters)

    def reset_attributes(self):
        for data in self.data_all:
            attr = data.get_attributes()
            character = data.get_class_enum()
            attr_start = character.starting_attributes()
            vitality_loss = attr[E_Attributes.AT_VITALITY] - attr_start[E_Attributes.AT_VITALITY]
            energy_loss = attr[E_Attributes.AT_ENERGY] - attr_start[E_Attributes.AT_ENERGY]
            hp_current = Data.parse_HMS(attr[E_Attributes.AT_MAX_HP])
            stamina_current = Data.parse_HMS(attr[E_Attributes.AT_MAX_STAMINA])
            mana_current = Data.parse_HMS(attr[E_Attributes.AT_MAX_MANA])
            hp_loss = character.effect_of_attribute_points(E_Attributes.AT_VITALITY, vitality_loss)[E_Attributes.AT_MAX_HP]
            stamina_loss = character.effect_of_attribute_points(E_Attributes.AT_VITALITY, vitality_loss)[E_Attributes.AT_MAX_STAMINA]
            mana_loss = character.effect_of_attribute_points(E_Attributes.AT_ENERGY, energy_loss)[E_Attributes.AT_MAX_MANA]
            attr[E_Attributes.AT_MAX_HP] = self._subtract_and_encode_quarter_tuples(hp_current, hp_loss)
            attr[E_Attributes.AT_MAX_MANA] = self._subtract_and_encode_quarter_tuples(stamina_current, stamina_loss)
            attr[E_Attributes.AT_MAX_STAMINA] = self._subtract_and_encode_quarter_tuples(mana_current, mana_loss)

            stat_points = attr[E_Attributes.AT_UNUSED_STATS] if E_Attributes.AT_UNUSED_STATS in attr else 0
            for key in attr_start:
                stat_points += attr[key] - attr_start[key]
                attr[key] = attr_start[key]
            print(f"Attempting to reset {data.get_name(True)}'s {stat_points} spent attribute points.")
            attr[E_Attributes.AT_UNUSED_STATS] = stat_points

            data.set_attributes(attr)
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def reset_skills(self):
        for data in self.data_all:
            n_skills = sum(data.get_skills())
            print(f"Attempting to reset {data.get_name(True)}'s {n_skills} learned skills.")
            skillset = [0] * 30
            data.set_skills(skillset)
            # That boost command also does the updating and saving!
            self.boost(E_Attributes.AT_UNUSED_SKILLS, n_skills)

    def enable_nightmare(self):
        for data in self.data_all:
            data.enable_nightmare()
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def enable_hell(self):
        for data in self.data_all:
            data.enable_hell()
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def enable_nirvana(self):
        for data in self.data_all:
            data.enable_nirvana()
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def enable_godmode(self):
        for data in self.data_all:
            print(f"Enabling GOD MODE for {data.get_name(True)}.")
            data.enable_godmode()
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def disable_godmode(self):
        for data in self.data_all:
            print(f"Disabling GOD MODE for {data.get_name(True)}.")
            data.disable_godmode()
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def redeem_golem(self, data: Data):
        item_analysis = Item(data.data)
        if not data.has_iron_golem:
            print("There is no golem to redeem.")
            return
        items = item_analysis.get_block_items(E_ItemBlock.IB_IRONGOLEM)
        if not items:
            return
        index_golem_code = items[0].index_start - 1
        data.data = data.data[:index_golem_code] + b'\x00'
        data.place_items_into_storage_maps(items)
        if self.is_standalone:
            data.update_all()
            data.save2disk()

    def drop_horadric(self, data: Data):
        """Drops all items from the Horadric Cube. If standalone mode, also saves the results to disk."""
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        # [Note: Iterate in reversed order, so that dropping front items will not destroy indices for back items.]
        for item in reversed(items):
            data.drop_item(item)
        if self.is_standalone:
            data.update_all()
            data.save2disk()
            print(f"Dropped {len(items)} items from the Horadric cube.")

    def empty_sockets_horadric(self, data: Data):
        # [Note: A bit convoluted. This function alters item locations and hence item indices are obsoleted.
        #  To compensate, get_cube_contents() is called anew on each iteration.]
        items = list()  # type: List[Item]
        c = 0
        found_a_target = True
        while (c < 6) and found_a_target:
            c = c + 1
            items = Item(data.data).get_cube_contents()  # type: List[Item]
            found_a_target = False
            for item in items:
                if item.n_sockets_occupied:
                    data.separate_socketed_items_from_item(item)
                    found_a_target = True
                    break
        if self.is_standalone:
            data.update_all()
            data.save2disk()
            print(f"Attempts were made to desocket Horadric Cube content. {len(items)} items were involved (socketed and base).")

    def set_sockets_horadric(self, data: Data, count: int):
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        for j in reversed(range(len(items))):
            data.set_sockets(items[j], count)
        if self.is_standalone:
            data.update_all()
            data.save2disk()

    def dispel_magic_horadric(self, data: Data):
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        for j in reversed(range(len(items))):
            data.dispel_magic(items[j])
        if self.is_standalone:
            data.update_all()
            data.save2disk()

    def toggle_ethereal(self, data: Data):
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        for item in items:
            data.set_ethereal(item)
        if self.is_standalone:
            data.update_all()
            data.save2disk()

    def jewelize_horadric(self, data: Data, tpl: E_ItemTpl):
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        for item in items:
            data.jewelize(item, do_replace=True, tpl=tpl)
        if self.is_standalone:
            data.update_all()
            data.save2disk()

    @staticmethod
    def _parse_difficulty_bitmap(data: Data, code: str) -> Dict[E_Progression, str]:
        codes = code.split('-', 1)
        bm = codes[-1]
        if len(codes) < 2:
            difficulty = data.highest_difficulty
        else:
            try:
                difficulty = E_Progression(int(codes[0]))
            except ValueError:
                _log.warning(f"Unable to parse waypoint or quest code '{code}'. Doing nothing for '{data.get_name(True)}'.")
                return dict()
        return {difficulty: re.sub("[^0-1]", '.', bm)}

    def set_waypoints(self, code: str):
        for data in self.data_all:
            data.waypoint_map = self._parse_difficulty_bitmap(data, code)
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def set_quests(self, code: str):
        for data in self.data_all:
            data.set_quests_simplified(self._parse_difficulty_bitmap(data, code))
            if self.is_standalone:
                data.update_all()
                data.save2disk()

    def regrade_horadric(self, data: Data):
        items = Item(data.data).get_cube_contents()  # type: List[Item]
        for item in items:
            data.regrade(item)
        if self.is_standalone:
            data.update_all()
            data.save2disk()

    def ensure_horadric(self, data: Data):
        if data.has_horadric_cube:
            return  # << Nothing to do.
        item_master = Item(data.data)
        items_in_non_existing_cube = Item(data.data).get_cube_contents()  # type: List[Item]
        data.drop_items(items_in_non_existing_cube)
        items_inventory = list(filter(lambda x: x.row <= 1 and x.col <= 1 and x.stash_type == E_ItemStorage.IS_INVENTORY,
                                      item_master.get_block_items(E_ItemBlock.IB_PLAYER, E_ItemParent.IP_STORED, None, stored=E_ItemStorage.IS_INVENTORY)))  # type: List[Item]
        if items_inventory:
            code = b''
            n_items = 1
            data.drop_items(items_inventory)
            for item in items_inventory:
                item.stash_type = E_ItemStorage.IS_CUBE
                n_items = n_items + 1
                code += item.data_item
            data.add_items_to_player(int.to_bytes(n_items) + data_tpl_horadric_cube + code)
        else:
            data.add_items_to_player(int.to_bytes(1) + data_tpl_horadric_cube)
        if self.is_standalone:
            data.update_all()
            data.save2disk()
        print("Horadric Cube has been added to the top left corner of the inventory. Old items in this place have been moved into the cube.")

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
        return res

    def save_horadric(self, pfname_out: str):
        """Writes the horadric cube raw contents to disk. Employs that these contents are in order.
        Target file structure: Number of main items, bytes block of all cube items."""
        data = self.data_all[0]
        res = self.grep_horadric(data)
        with open(expanduser(pfname_out), 'wb') as OUT:
            OUT.write(res)
        print(f"Wrote file '{pfname_out}'.")

    @staticmethod
    def create_rune_cube(cmd: str):
        (pfname, runes) = cmd.split(":",1)
        runes = list(filter(lambda x: x is not None, [E_Rune.from_name(r) for r in runes.split(",")]))
        content = b''
        for j in range(len(runes)):
            row = floor(j / 3)
            col = j % 3
            item = Item.create_rune(runes[j], E_ItemStorage.IS_CUBE, row=row, col=col)
            if item is None or item.data_item is None:
                continue
            content = content + item.data_item
            print(f"Adding: {item}")
        with open(pfname, 'wb') as OUT:
            OUT.write(content)
        print(f"Wrote runic cube with {len(runes)} runes to '{pfname}'")

    def insert_horadric(self, data: Data, items: bytes):
        """Takes a byte block of Horadric cube player items and moves it into the players Horadric Cube.
        Replaces old contents.
        After this is done the character file is saved automatically."""
        self.drop_horadric(data)
        data.add_items_to_player(items)
        if self.is_standalone:
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
$ python3 {Path(sys.argv[0]).name} --info conan.d2s ormaline.d2s"""
        parser = argparse.ArgumentParser(prog='horazons_folly.py', description=desc, epilog=epilog, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--omit_backup', action='store_true',
            help="Per default, target files will be back-upped to .backup files. For safety. This option will disable that safety.")
        parser.add_argument('--pfname_backup', type=str, help='State a pfname to the backup file. Per default a timestamped name will be used. If there are multiple files to backup, the given name will be prefixed with each character\'s name.')
        parser.add_argument('--exchange_horadric', action='store_true', help="Flag. Requires that there are precisely 2 character pfnames given. This will exchange their Horadric Cube contents.")
        parser.add_argument('--create_rune_cube', type=str, nargs='?', const='enigmatic_rune_cube.cube:jah,ith,ber', help="pfname, ':', then a comma separated list of up to 12 rune names and/or gem codes, /[tasredb][0-4]/. Creates a cube content with these runes and socketables.")
        parser.add_argument('--drop_horadric', action='store_true', help="Flag. If given, the Horadric Cube contents of the targeted character will be removed.")
        parser.add_argument('--save_horadric', type=str, help="Write the items found in the Horadric Cube to disk with the given pfname. Only one character allowed.")
        parser.add_argument('--load_horadric', type=str, help="Drop all contents from the Horadric Cube and replace them with the horadric file content, that had been written using --save_horadric earlier.")
        parser.add_argument('--empty_sockets_horadric', action='store_true', help="Flag. Pull all socketed items from items in the horadric cube. Try to preserve these socketables.")
        parser.add_argument('--set_sockets_horadric', type=int, help="Attempt to set this many sockets to the socket-able items in the horadric cube.")
        parser.add_argument('--dispel_magic', action='store_true', help='Flag. Acts on magical, rare, and crafted items within the Horadric Cube, dispelling their magic.')
        parser.add_argument('--toggle_ethereal', action='store_true', help="Flag. For each item within the Horadric Cube toggle the ethereal state.")
        parser.add_argument('--jewelize', nargs='?', const='jew', type=str, help="Will attempt to turn magic items within the Horadric Cube into jewels (if 'jew' is passed, or small charms, rings or amulets, if 'cm1', 'rin' or 'amu' is passed).")
        parser.add_argument('--regrade_horadric', action='store_true', help="Flag. For each item within the Horadric Cube upgrade it (usually normal, exceptional, elite). After max grade returns to normal.")
        parser.add_argument('--ensure_horadric', action='store_true', help="Flag. If the player has no Horadric Cube, one will be created in the inventory. Any item in that location will be put into the cube instead.")
        parser.add_argument('--hardcore', action='store_true', help="Flag. Set target characters to hard core mode.")
        parser.add_argument('--softcore', action='store_true', help="Flag. Set target characters to soft core mode.")
        parser.add_argument('--revive_self', action='store_true', help="Flag. If your character is dead, this will revive him. Even if he is a hardcore character. He still may have to pick up his corpse though.")
        parser.add_argument('--revive_merc', action='store_true', help="Flag. If your mercenary is dead, this will revive him.")
        parser.add_argument('--redeem_golem', action='store_true', help="Flag. If there is an iron golem, dispel it and return its items into the player's inventory.")
        parser.add_argument('--boost_attributes', type=int, help='Set this number to the given value.')
        parser.add_argument('--boost_skills', type=int, help='Set this number to the given value.')
        parser.add_argument('--reset_attributes', action="store_true", help="Flag. Returns all spent attribute points for redistribution.")
        parser.add_argument('--reset_skills', action='store_true', help="Flag. Unlearns all skills, returning them as free skill points.")
        parser.add_argument('--enable_nightmare', action='store_true', help="Flag. Enables entering nightmare. Fully upgrades character to level 38 and gives gold to match.")
        parser.add_argument('--enable_hell', action='store_true', help="Flag. Enables entering hell and nightmare. Fully upgrades character to level 68 and gives gold to match.")
        parser.add_argument('--enable_nirvana', action='store_true', help="Flag. Empowers the character to level 86 and sets him up as victor of hell. Also gives gold to match.")
        parser.add_argument('--enable_godmode', action='store_true', help="Enables Demigod-mode (so far without high Mana/HP/Stamina). Creates a .humanity stat file alongside the .d2s for later return to normal mode.")
        parser.add_argument('--disable_godmode', action='store_true', help="Returns to human form (retaining skill points earned in god mode). After all, who wants the stress of being super all the time?")
        parser.add_argument('--info', action='store_true', help="Flag. Show some statistics to each input file.")
        parser.add_argument('--info_stats', action='store_true', help='Flag. Nerd-minded. Detailed info tool on the parsing of attributes and skills.')
        parser.add_argument('--set_waypoints', type=str, help="Set waypoints as optional prefix /INDEX_DIFFICULTY-/ and bitmap /.{39}/ where 0/1 means off/on and everything else is ignored.")
        parser.add_argument('--set_quests', type=str, help="Set quests as optional prefix /INDEX_DIFFICULTY-/ and bitmap /.{27}/ where 0/1 means reset/completed and everything else is ignored.")
        parser.add_argument('pfnames', nargs='*', type=str, help='List of path and filenames to target .d2s character files.')
        parsed = parser.parse_args(args)  # type: argparse.Namespace
        return parsed

if __name__ == '__main__':
    hor = Horadric()
    print("Done.")

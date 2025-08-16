#!/usr/bin/python3
"""
Incubus script. Finally decided on a third python file. Mostly, because the
original parser workhorse, horazons_folly.py, is growing far too large,
this day exceeding 4000 lines of code already.

This script is about parsing magic sequences, as are defined in neighboring
mods.tsv. It will allow, both, creating human-readable string representations,
as well, as creating altered modifications strings for inserting into existing
extended Items.

It will become a dependency of horazons_folly.py, but also offer elementary
command line functionality as a stand-alone script.

Markus-Hermann Koch, mhk@markuskoch.eu, 2025/08/11

Notes:
======
* All bit sequences handled herein are expected as little endian and
  strictly processed as such. It was a design flaw in Horazon's Folly
  to dabble in big endian binaries at all.

Literature:
===========
* [1]: Tab-separated list of modifications with parameters and rules that I managed to guess with confidence.
*   ./src/mods.tsv
"""

from __future__ import annotations

import os
import re
import logging
import argparse
from Tools.i18n.pygettext import is_literal_string
from collections import OrderedDict as odict
from argparse import RawTextHelpFormatter
from numbers import Number
from pathlib import Path
from math import ceil, floor
from shutil import which
from typing import List, Dict, Optional, Union, Tuple, OrderedDict, Any
from enum import Enum


# > Config.sys. ------------------------------------------------------
pfname_mods_tsv = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mods.tsv'))
# < ------------------------------------------------------------------


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


"""Example string: Infinity.
On Kill: Autocast[0:32](6i[9:15]level(20)9s[15:24], (Chain Lightning)0[24:25], (0)7i[25:32], (50)%)
Aura on Equip[32:55](9s[41:50](Conviction)5i[50:55], +(12))
Faster Run and Walk (%)[55:71](7i20[64:71](35)%)
Enhanced Damage[71:98](9i[80:89](325)%=9i[89:98], (325)%)
Reduce Enemy Lightning Resist[98:115](8i[107:115]-(55)%)
Crushing Blow Probability[115:131](7i[124:131](40)%)
Prevent Monster Healing[131:147](1000000[140:147](1))
Vitality Bonus based on Char Level[147:162](6f3[156:162]Level *(0.5))
Magic Find[162:179](8i100[171:179](30)%)
On Being Struck: Autocast[179:211](6i[188:194]level(21)9s[194:203], (Cyclone Armor)0[203:204], (0)7i[204:211], (10)%)"""
example_infinity = "00100011000101010101100000100110111010010110111100001100000011001110110100010000101000101101000101011100101111011000001000100001010101011100100000011111011000100000001010001000001100100110101010110101110001010001111111110000"

"""This is most ugly. Due to incubus.py being a dependency of horazons_folly.py it is difficult to import
d_skills and E_Characters from there. Attempts, to do this, led to an unstable program. Not wanting to create
a fourth .py file for this, nor to put these central elements into small incubus.py, I decided to go with
a redundant copy for now. As said: Ugly. But also: Works."""
redundant_skills = {
    'amazon': ["Magic Arrow", "Fire Arrow", "Inner Sight", "Critical Strike", "Jab",
                             "Cold Arrow", "Multiple Shot", "Dodge", "Power Strike", "Poison Javelin",
                             "Exploding Arrow", "Slow Missiles", "Avoid", "Impale", "Lightning Bolt",
                             "Ice Arrow", "Guided Arrow", "Penetrate", "Charged Strike", "Plague Javelin",
                             "Strafe", "Immolation Arrow", "Decoy", "Evade", "Fend",
                             "Freezing Arrow", "Valkyrie", "Pierce", "Lightning Strike", "Lightning Fury"],
    'sorceress': ["Fire Bolt", "Warmth", "Charged Bolt", "Ice Bolt", "Frozen Armor",
                                "Inferno", "Static Field", "Telekinesis", "Frost Nova", "Ice Blast",
                                "Blaze", "Fireball", "Nova", "Lightning", "Shiver Armor",
                                "Fire Wall", "Enchant", "Chain Lightning", "Teleport", "Glacial Spike",
                                "Meteor", "Thunder Storm", "Energy Shield", "Blizzard", "Chilling Armor",
                                "Fire Mastery", "Hydra", "Lightning Mastery", "Frozen Orb", "Cold Mastery"],
    'necromancer': ["Amplify Damage", "Teeth", "Bone Armor", "Skeleton Mastery", "Raise Skeleton",
                                  "Dim Vision", "Weaken", "Poison Dagger", "Corpse Explosion", "Clay Golem",
                                  "Iron Maiden", "Terror", "Bone Wall", "Golem Mastery", "Skeletal Mage",
                                  "Confuse", "Life Tap", "Poison Explosion", "Bone Spear", "Blood Golem",
                                  "Attract", "Decrepify", "Bone Prison", "Summon Resist", "Iron Golem",
                                  "Lower Resist", "Poison Nova", "Bone Spirit", "Fire Golem", "Revive"],
    'paladin': ["Sacrifice", "Smite", "Might", "Prayer", "Resist Fire",
                              "Holy Bolt", "Thorns", "Holy Fire", "Defiance", "Resist Cold",
                              "Zeal", "Charge", "Blessed Aim", "Cleansing", "Resist Lightning",
                              "Vengeance", "Blessed Hammer", "Concentration", "Holy Freeze", "Vigor",
                              "Conversion", "Holy Shield", "Holy Shock", "Sanctuary", "Meditation",
                              "Fist of the Heavens", "Fanaticism", "Conviction", "Redemption", "Salvation"],
    'barbarian': ["Bash", "Sword Mastery", "Axe Mastery", "Mace Mastery", "Howl", "Find Potion",
                                "Leap", "Double Swing", "Polearm Mastery", "Throwing Mastery", "Spear Mastery", "Taunt", "Shout",
                                "Stun", "Double Throw", "Increased Stamina", "Find Item",
                                "Leap Attack", "Concentrate", "Iron Skin", "Battle Cry",
                                "Frenzy", "Increased Speed", "Battle Orders", "Grim Ward",
                                "Whirlwind", "Berserk", "Natural Resistance", "War Cry", "Battle Command"],
    'druid': ["Raven", "Poison Creeper", "Werewolf", "Lycanthropy", "Firestorm",
                            "Oak Sage", "Summon Spirit Wolf", "Werebear", "Molten Boulder", "Arctic Blast",
                            "Carrion Wine", "Feral Rage", "Maul", "Fissure", "Cyclone Armor",
                            "Heart of Wolverine", "Summon Dire Wolf", "Rabies", "Fire Claws", "Twister",
                            "Solar Creeper", "Hunger", "Shockwave", "Volcano", "Tornado",
                            "Spirit of Barbs", "Summon Grizzly", "Fury", "Armageddon", "Hurricane"],
    'assassin': ["Fire Blast", "Claw Mastery", "Psychic Hammer", "Tiger Strike", "Dragon Talon",
                               "Shock Web", "Blade Sentinel", "Burst of Speed", "Fists of Fire", "Dragon Claw",
                               "Charged Bolt Sentry", "Wake of Fire", "Weapon Block", "Cloak of Shadows", "Cobra Strike",
                               "Blade Fury", "Fade", "Shadow Warrior", "Claws of Thunder", "Dragon Tail",
                               "Lightning Sentry", "Wake of Inferno", "Mind Blast", "Blades of Ice", "Dragon Flight",
                               "Death Sentry", "Blade Shield", "Venom", "Shadow Master", "Phoenix Strike"]
}


class E_ColumnType(Enum):
    CT_NO = 0
    CT_NAME = 1
    CT_ID = 2
    CT_LABEL_0 = 3
    CT_LABEL_1 = 4
    CT_LABEL_2 = 5
    CT_LABEL_3 = 6
    CT_LABEL_4 = 7
    CT_PARAM_0 = 8
    CT_PARAM_1 = 9
    CT_PARAM_2 = 10
    CT_PARAM_3 = 11
    CT_PARAM_4 = 12
    CT_EXAMPLE = 13
    CT_COMMENT = 14

class E_StateMod(Enum):
    """State enum for the Modification class."""
    SM_OK = 0
    SM_ID_UNKNOWN = 1
    SM_INVALID_VALUE = 2


class TableMods:
    """Wrapper class for the mods.tsv content. For easy access to core features."""
    def __init__(self, pfname: Optional[str] = None):
        self.pfname = pfname
        self.data = TableMods.read_mods_tsv(pfname)

    @staticmethod
    def read_mods_tsv(pfname: Optional[str] = None) -> List[Dict[E_ColumnType, str]]:
        """:param pfname: Target pfname to the .tsv file."""
        if pfname is None:
            pfname = pfname_mods_tsv
        if not Path.is_file(Path(pfname)):
            _log.error(f"Failure to load modification .tsv file '{pfname}'. Returning empty data structure.")
            return list()
        res = list()  # type: List[Dict[E_ColumnType, str]]
        with (open(pfname, 'r') as IN):
            # [Note: Eat the header line!]
            IN.readline()
            n_columns = len(list(E_ColumnType))

            def parse_line(line_: str) -> Optional[Dict[E_ColumnType, str]]:
                entries = line_.rstrip().split("\t", n_columns - 1)
                if not entries:
                    return None
                res_ = dict()  # type: Dict[E_ColumnType, str]
                for j in range(n_columns):
                    tp = E_ColumnType(j)
                    if tp == E_ColumnType.CT_NO:
                        continue  # << Is useful in the .ods file only, for sorting the table.
                    res_[tp] = entries[j] if j < len(entries) else ''
                if (E_ColumnType.CT_ID not in res_) or bool(re.match("^[0-1]{9}$", res_[E_ColumnType.CT_ID])) == False:
                    return None
                # else: res_[E_ColumnType.CT_NO] = int(res_[E_ColumnType.CT_ID][::-1], 2)
                return res_

            while True:
                line = IN.readline()
                if not line:
                    break
                entry = parse_line(line)
                if entry:
                    res.append(entry)
        return res

    def get_line_by_id(self, id_mod: str) -> Optional[Dict[E_ColumnType, str]]:
        """:param id_mod: Modification id as little endian binary string of length 9. E.g., '011011000' for cold damage.
        :returns a dict of the line identified by id_mod. Or None in case of failure."""
        ind = [id_mod == val[E_ColumnType.CT_ID] for val in self.data]
        return self.data[ind.index(True)] if True in ind else None

    def __str__(self) -> str:
        return f"Table with {len(self.data)} rows from '{self.pfname}'." if self.data else f"Empty table from '{self.pfname}'."


class ModificationParameter:
    """Class for parsing and using a single modification template, for a single value. E.g., '6i50'."""
    cache_parsed = dict()
    """Cache for parsed templates."""

    def __init__(self, param: str):
        """:param param: A mod parameter like '>6i50'. See ./doc/general_science/readme_mods.txt for details."""
        self.param = param
        # Convenience members for holding an index0 within a larger binary where this parameter instance is sited in.
        self._index0 = None  # type: Optional[int]
        # Convenience members for holding an index1 within a larger binary where this parameter instance is sited in.
        self._index1 = None  # type: Optional[int]

    @staticmethod
    def int2binary(val: int, n_bits: int) -> str:
        """:returns a little endian binary representation of n_bits from given int val. The  return string will be >=0
        and also capped at the maximum allowed by the number of bits. Hence, range is {0,..,2^{n_bits}-1}."""
        if n_bits < 0:
            raise ValueError(f"Number of bits must be >=0. '{n_bits}' has been encountered.")
        elif n_bits == 0:
            return ''
        if val < 0:
            val = 0
        elif val >= 2**n_bits:
            val = 2**n_bits - 1
        binary = '{0:b}'.format(val)[::-1]
        return binary + ('0' * (n_bits - len(binary)))

    @staticmethod
    def binary2int(binary: str) -> int:
        """:returns an int representation of given little endian binary."""
        return int(binary[::-1], 2)

    @staticmethod
    def parse(param: str) -> Optional[Dict[str, Union[str, int, None]]]:
        """Parses a parameter code into its components.
        :param param: A mod parameter like '>6i50'. See ./doc/general_science/readme_mods.txt for details.
        :returns a dict or None in case of failure. Structure:
          'literal': Binary of a constant literal. Or None, if param is not a literal.
            Literals are always interpreted as plain integers.
          'relation': '>' or '='. It is a requirement that a value of this param structure is either >=
            or = to a value that has been preceding it.
          'n_bits': Number of bits that is expected for this structure template.
          'tp': Value type. 'i' in case of integers, 'f' in case of floats, '' in case of literals.
          'offset': In case of integers this is the offset that has to be added to the in-game value to reach
            the save-game representation. E.g. '10' for armor class. In-Game armor of 100 is saved as 110.
            In case of little endian binary floats this defines the position of the point. 0 equals an integer.
            The higher the offset, the further the point moves to the right."""
        if param in ModificationParameter.cache_parsed:
            return ModificationParameter.cache_parsed[param]
        if not param:
            return None
        res = dict() # type: Dict[str, Union[str, int]]

        # Regex: Find out about literals.
        search_literal = re.search('^([>=]?)([0-9]+)$', param)
        is_literal = True if search_literal else False
        res['literal'] = search_literal.groups()[1] if is_literal else None

        # Regex: Parse the entire param.
        search_all = re.search("^([>=]?)([0-9]*)([fis]?)([0-9]*)$", param)
        if search_all is None:
            _log.warning(f"Encountered invalid modification parameter '{param}. Returning None.'")
            return None
        groups_all = search_all.groups()
        res['relation'] = groups_all[0]
        if is_literal:
            res['n_bits'] = len(res['literal'])
        else:
            res['n_bits'] = int(groups_all[1]) if len(groups_all[1]) else 0
        res['tp'] = groups_all[2]
        res['offset'] = int(groups_all[3]) if len(groups_all[3]) else 0
        ModificationParameter.cache_parsed['param'] = res
        return res

    @property
    def is_skill(self) -> bool:
        """:returns True if and only if self.param equals '9s', signifying a skill id."""
        return isinstance(self.param, str) and ('9s' == self.param)

    @staticmethod
    def get_name_skill(id_skill: Union[int, str]) -> str:
        """Takes a string id and returns a human-readable name. E.g., '54' is the Sorceress spell 'Teleport'. Compare 'Skills.txt'."""
        if isinstance(id_skill, str):
            id_skill = int(id_skill[::-1], 2)
        if 6 <= id_skill < 36:
            character = 'amazon'
            offset = 6
        elif 36 <= id_skill < 66:
            character = 'sorceress'
            offset = 36
        elif 66 <= id_skill < 96:
            character = 'necromancer'
            offset = 66
        elif 96 <= id_skill < 126:
            character = 'paladin'
            offset = 96
        elif 126 <= id_skill < 156:
            character = 'barbarian'
            offset = 126
        elif 221 <= id_skill < 251:
            character = 'druid'
            offset = 221
        elif 251 <= id_skill < 281:
            character = 'assassin'
            offset = 251
        else:
            return 'no skill'
        index = id_skill - offset
        return redundant_skills[character][index] if index < len(redundant_skills[character]) else f'unknown skill ({id_skill})'

    @property
    def code(self) -> Optional[Dict[str, Union[str, int, None]]]:
        return self.parse(self.param)

    @property
    def range(self) -> Union[Tuple[int, int], Tuple[float, float]]:
        """:returns the valid range of values for this ModificationParameter."""
        code = self.code
        if code['literal'] is not None:
            val = self.binary2int(code['literal'])
            return val, val
        elif code['tp'] == 'i':
            return (-code['offset']), (2**code['n_bits'] - code['offset'] - 1)
        elif code['tp'] == 'f':
            return 0, (2**(code['n_bits']-code['offset']) - 2**(-code['offset']))
        else:
            raise ValueError(f"Unsupported type code '{code['tp']}' encountered.")

    @property
    def n_bits(self) -> int:
        code = self.code
        return code['n_bits'] if code else 0

    def val2bin_templated(self, val: Optional[Union[int, float]], val_prior: Optional[Union[int, float]] = None) -> Optional[str]:
        """Converts an in-game value into a little endian binary sequence according to this object's spec."""
        if val is None:
            return None
        codes = self.code
        if (val_prior is not None) and ((codes['relation'] == '>' and val < val_prior) or (codes['relation'] == '=')):
            val = val_prior
        if codes is None:
            return None
        elif codes['tp'] == '':
            binary = codes['literal']
        elif codes['tp'] == 'i':
            binary = self.int2binary(int(val) + codes['offset'], codes['n_bits'])
        elif codes['tp'] == 'f':
            binary = self.int2binary(int((2**codes['offset']) * val), codes['n_bits'])
        else:
            return None
        return binary

    def bin2val_templated(self, binary: Optional[str]) -> Optional[Union[int, float]]:
        """Translates a binary sequence to a numeric value, according to the rules of this template."""
        if binary is None:
            return None
        codes = self.code
        if codes is None:
            return None
        elif len(binary) != codes['n_bits']:
            raise ValueError(f"Binary sequence '{binary}' does not fit numeric template '{self.param}'.")
        elif codes['tp'] == '':
            val = self.binary2int(codes['literal'])
        elif codes['tp'] == 'i':
            val = self.binary2int(binary) - codes['offset']
        elif codes['tp'] == 'f':
            val = float(self.binary2int(binary)) / (2 ** codes['offset'])
        else:
            return None
        return val

    @property
    def has_relation(self) -> bool:
        """:returns True if and only if this ModificationParameter has a valid parameter and a non-trivial relation symbol."""
        code = self.code
        return False if ((code is None) or (code['relation'] == '')) else True

    def does_binary_match(self, binary: str, binary_prior: Optional[str] = None) -> bool:
        """Does the given little endian binary match this Modification?
        :param binary: LE binary code to be matched.
        :param binary_prior: A potential prior binary code. Relevant, if self.param has a relation symbol.
        :returns True of and only if given binary would be a valid value for this ModificationParameter."""
        code = self.code
        if code is None:
            _log.warning(f"This ModificationParameter has no valid parameter to check against: '{self.param}'.")
            return False
        regexp = '^[0-9]{' + str(code['n_bits']) + '}$'
        is_fit = bool(re.match(regexp, binary))
        if is_fit and self.has_relation and (binary_prior is not None):
            if code['relation'] == '=':
                is_fit = (int(binary[::-1], 2) == int(binary_prior[::-1], 2))
            elif code['relation'] == '>':
                is_fit = (int(binary[::-1], 2) >= int(binary_prior[::-1], 2))
            else:
                raise ValueError(f"Unsupported relation symbol '{code['relation']}' encountered.")
        return is_fit

    @property
    def index0(self) -> Optional[int]:
        return self._index0

    @property
    def index1(self) -> Optional[int]:
        return self._index1

    def set_indices(self, binary0: Optional[str] = None, index0: int = 0, index_prior: Optional[int] = None) -> bool:
        """Will reset self._index0 and self._index1 to None in case of failure. Else will set them thus, that they
        limit this Parameter instance's binary code within given binary0.
        :param binary0: A complete modification set binary. It may be None, to reset these indices.
        :param index0: Index within binary0 where this Modification Parameter instance is sited.
        :param index_prior: If 0<=index_prior<(index0-9) will use that sequence in binary0 for prior value.
        :returns True if and only if setting and included parameter verification succeeded.
          False if the tested binary does not fit this Parameter."""
        self._index0 = None
        self._index1 = None
        if binary0 is None:
            return True  # << This is no crime.
        index1 = index0 + self.n_bits
        if len(binary0) < index1:
            _log.error(f"Given binary is too short for this parameter of length '{self.n_bits}' being sited at index '{index0}': '{binary0}'.")
            return False
        binary = binary0[index0:index1]
        binary_prior = binary0[index_prior:index0] if ((index_prior is not None) and (0 <= index_prior < index0)) else None
        if (binary is not None) and not self.does_binary_match(binary, binary_prior):
            _log.error(f"Given binary '{binary}' at index0 '{index0}' does not fit template '{self.param}.")
            return False
        self._index0 = index0
        self._index1 = index1
        return True

    def __str__(self) -> str:
        return f"{self.param}[{self.index0}:{self.index1}]"

class ModificationItem:
    """Small class for analyzing one specific modification. Like, e.g., oSkill Teleport +1:
      '100001100011011000100000' (i.e., 9-bit-id oskill: 100001100 Teleport: 011011000 "+1": 100000)
    :param binary: Binary string describing an entire item modification set. Comprising ids and all attached parameters.
    :param index0: Starting index within binary this specific Modification Item is concerned with.
    :param table_mods: Modification lookup table."""
    def __init__(self, binary: str, index0: int, table_mods: TableMods):
        self.binary = str(binary)
        self.index0 = index0
        if (len(binary) < (9 + index0)) or not bool(re.match("^[0-1]+$", binary)):
            raise ValueError(f"Invalid binary source string '{binary}' encountered.")
        self.table_mods = table_mods
        self.parsed = self.parse_parameters(self.binary, self.index0, self.table_mods)

    @property
    def id_mod(self) -> Optional[str]:
        """:returns the id of this mod if such a """
        return None if len(self.binary) < (9 + self.index0) else self.binary[self.index0:(9+self.index0)]

    @property
    def is_valid(self) -> bool:
        return True if (self.parsed is not None) and (self.parsed['is_valid']) else False

    @staticmethod
    def parse_parameters(binary: str, index0: int, table: TableMods) -> Dict[str, Any]:
        """Attempts to parse the given binary into a list of parameters. If successful, this will describe an
        entire magical property.
        :param binary: A little endian binary string describing a complete modification set.
        :param index0: Index within binary of the modification id we are interested in.
        :param table: Table of known modification specifications.
        :returns dict.
          'is_valid': bool. Was a known modification type found and could it be parsed?
          'index0': int. Repeats the given index0.
          'index1': index within binary of the first entry beyond this modification item.
            May be == len(binary) if this is the last item or if this modification could not be identified,
            making it a residual (which is not valid).
          'parameters': List of ModificationParameter. Will be empty if this not 'is_valid'.
            Else will hold the entire list of ModificationParameters this item is concerned with."""
        # [Note: Initializing as failure case, leading to a residual binary. Anything better needs to be earned.]
        res = {
            'is_valid': False,
            'index0': index0,
            'index1': len(binary),
            'parameters': list()  # type: List[ModificationParameter]
        }  # type: Dict[str, Any]
        if len(binary) < (index0 + 9):
            return res
        id_mod = binary[index0:(index0 + 9)]
        spec = table.get_line_by_id(id_mod)
        if spec is None:
            return res
        params = list()
        index_prior = None
        index_current = index0 + 9
        for key in [E_ColumnType.CT_PARAM_0, E_ColumnType.CT_PARAM_1, E_ColumnType.CT_PARAM_2, E_ColumnType.CT_PARAM_3, E_ColumnType.CT_PARAM_4]:
            if not spec[key]:
                break
            param = ModificationParameter(spec[key])
            acceptable = param.set_indices(binary, index_current, index_prior)
            if not acceptable:
                return res
            params.append(param)
            index_prior = index_current
            index_current = param.index1
        res['index1'] = index_current
        res['parameters'] = params
        res['is_valid'] = True
        return res

    def __str__(self) -> str:
        spec = self.table_mods.get_line_by_id(self.id_mod)
        if spec is None:
            return f"Hitherto unknown modification[{self.parsed['index0']}:{self.parsed['index1']}] with id '{self.binary[self.parsed['index0']:(self.parsed['index0']+9)]}'."
        res = f"{spec[E_ColumnType.CT_NAME]}[{self.parsed['index0']}:{self.parsed['index1']}]"
        params = self.parsed['parameters']  # type: List[ModificationParameter]
        if params:
            res += '('
            for j in range(len(params)):
                param = params[j]
                param_binary = self.binary[param.index0:param.index1]
                if param.is_skill:
                    value = '(' + param.get_name_skill(param_binary) + ')'
                else:
                    value = f'({param.bin2val_templated(param_binary)})'
                prefix_suffix = spec[E_ColumnType(j + 3)].split(',', 1)
                if len(prefix_suffix) < 2:
                    prefix_suffix.append('')
                value = prefix_suffix[0] + value + prefix_suffix[1]
                if j > 0:
                    value = ', ' + value
                res += str(param) + value
            res += ')'
        return res

class ModificationSet:
    """Master class parsing a given Item's entire modification binary."""
    cache_table_mods = TableMods()  # type: TableMods

    def __init__(self, binary: str):
        """:param binary: Complete binary of a complete mod-section."""
        self.binary = binary
        self.items_modification = list()  # type: List[ModificationItem]
        index0 = 0
        while index0 < len(self.binary):
            mod = ModificationItem(self.binary, index0, self.cache_table_mods)
            if mod.id_mod == '111111111':
                # [Note: 512 is the code for the terminal id. It is no mod per se and should not be part of a mod list.]
                break
            self.items_modification.append(mod)
            if not mod.is_valid:
                # [Note: A non-valid mod is designed to hold the unparsable remainder binary and should be part of
                #  the modification list. Its chief problem is the first mod within it being hitherto unknown in [1].]
                break
            index0 = mod.parsed['index1']

    def __str__(self):
        res = self.binary + "\n"
        for mod in self.items_modification:
            res += str(mod) + "\n"
        res = res.rstrip()
        return res

if __name__ == '__main__':
    mods = TableMods()
    ms = ModificationSet(example_infinity)
    # #<< id: 001000110 lvl(20): 001010 skill(53): 101011000; val(100): 00100110
    print(ms)
    print('Done.')

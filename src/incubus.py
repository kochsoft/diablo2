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
from tokenize import group
from typing import List, Dict, Optional, Union, Tuple, OrderedDict, Any
from enum import Enum


# > Config.sys. ------------------------------------------------------
pfname_mods_tsv = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mods.tsv'))
# < ------------------------------------------------------------------


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


"""Example string: Infinity."""
example_infinity = "00100011000101010101100000100110111010010110111100001100000011001110110100010000101000101101000101011100101111011000001000100001010101011100100000011111011000100000001010001000001100100110101010110101110001010001111111110000"

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


class ParamMod:
    def __init__(self, param: str):
        """:param param: A mod parameter like '>6i50'. See ./doc/general_science/readme_mods.txt for details."""
        self.param = param

    @staticmethod
    def parse(param: str) -> Optional[Dict[str, Union[str, int, None]]]:
        """:param param: A mod parameter like '>6i50'. See ./doc/general_science/readme_mods.txt for details."""
        if not param:
            return None
        res = dict() # type: Dict[str, Union[str, int]]

        # Regex: Find out about literals.
        search_literal = re.search('^([>=]?)([0-9]+)$', param)
        is_literal = True if search_literal else False
        res['literal'] = search_literal.groups()[1] if is_literal else None

        # Regex: Parse the entire param.
        search_all = re.search("^([>=]?)([0-9]*)([fi]?)([0-9]*)$", param)
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
        return res

class Modification:
    """Small class for analyzing one specific modification.
    :param binary: Potentially the complete binary string this Incubus session is about.
    :param index0:"""
    def __init__(self, binary: str, index0: int, table_mods: TableMods):
        self.binary = str(binary)
        self.index0 = max(index0, 0)
        if len(binary) < (9 + index0) or not bool(re.match("^[0-1]+$", binary)):
            raise ValueError(f"Invalid binary source string '{binary}' encountered.")
        self.table_mods = table_mods

    @property
    def id_mod(self) -> Optional[str]:
        """:returns the id of this mod if such a """
        return None if len(self.binary) < self.index0 + 9 else self.binary[self.index0:(self.index0+9)]

    #def split(self) -> Optional[Dict[E_ColumnType, str]]: TODO! Hier war ich.
    #    """:returns"""
    #    id_mod = self.id_mod
    #    line = self.table_mods.get_line_by_id()


class Incubus:
    pass


if __name__ == '__main__':
    #mods = TableMods()
    #print(mods)
    print(ParamMod.parse('>1100'))
    print(ParamMod.parse('1100'))
    print(ParamMod.parse('6f5'))
    print(ParamMod.parse('=a6f5'))
    print('Done.')

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
from collections import OrderedDict as odict
from argparse import RawTextHelpFormatter
from pathlib import Path
from math import ceil, floor
from typing import List, Dict, Optional, Union, Tuple, OrderedDict, Any
from enum import Enum


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()


# > Config.sys. ------------------------------------------------------
pfname_mods_tsv = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mods.tsv'))
# < ------------------------------------------------------------------


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


def read_mods_tsv(pfname: Optional[str] = None) -> List[Dict[E_ColumnType, str]]:
    """Free function for reading mods.tsv."""
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
                res_[E_ColumnType(j)] = entries[j] if j < len(entries) else ''
            if (E_ColumnType.CT_ID not in res_) or bool(re.match("^[0-1]{9}$", res_[E_ColumnType.CT_ID])) == False:
                return None
            return res_
        while True:
            line = IN.readline()
            if not line:
                break
            entry = parse_line(line)
            if entry:
                res.append(entry)
    return res


class E_StateMod(Enum):
    """State enum for the Modification class."""
    SM_OK = 0
    SM_ID_UNKNOWN = 1
    SM_INVALID_VALUE = 2


class Modification:
    """Small class for analyzing one specific modification.
    :param binary: Potentially the complete binary string this Incubus session is about.
    :param index0:"""
    def __init__(self, binary: str, index0: int, mods_tsv: List[Dict[str]]):
        self.binary = binary
        self.mods_tsv = mods_tsv


class Incubus:
    pass


if __name__ == '__main__':
    mods = read_mods_tsv()
    print('Done.')

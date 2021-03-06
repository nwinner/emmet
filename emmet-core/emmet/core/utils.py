import datetime
from enum import Enum
from itertools import groupby, product
from pathlib import Path
from typing import Dict, Iterator, List

import bson
import numpy as np
from monty.json import MSONable
from monty.serialization import loadfn
from pydantic import BaseModel
from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
from pymatgen.core.structure import Structure
from typing_extensions import Literal

from emmet.core import SETTINGS


def get_sg(struc, symprec=SETTINGS.SYMPREC) -> int:
    """helper function to get spacegroup with a loose tolerance"""
    try:
        return struc.get_space_group_info(symprec=symprec)[1]
    except Exception:
        return -1


def group_structures(
    structures: List[Structure],
    ltol: float = SETTINGS.LTOL,
    stol: float = SETTINGS.STOL,
    angle_tol: float = SETTINGS.ANGLE_TOL,
    symprec: float = SETTINGS.SYMPREC,
) -> Iterator[List[Structure]]:
    """
    Groups structures according to space group and structure matching

    Args:
        structures ([Structure]): list of structures to group
        ltol (float): StructureMatcher tuning parameter for matching tasks to materials
        stol (float): StructureMatcher tuning parameter for matching tasks to materials
        angle_tol (float): StructureMatcher tuning parameter for matching tasks to materials
        symprec (float): symmetry tolerance for space group finding
    """

    sm = StructureMatcher(
        ltol=ltol,
        stol=stol,
        angle_tol=angle_tol,
        primitive_cell=True,
        scale=True,
        attempt_supercell=False,
        allow_subset=False,
        comparator=ElementComparator(),
    )

    def _get_sg(struc):
        return get_sg(struc, symprec=symprec)

    # First group by spacegroup number then by structure matching
    for _, pregroup in groupby(sorted(structures, key=_get_sg), key=_get_sg):
        for group in sm.group_structures(list(pregroup)):
            yield group


def jsanitize(obj, strict=False, allow_bson=False):
    """
    This method cleans an input json-like object, either a list or a dict or
    some sequence, nested or otherwise, by converting all non-string
    dictionary keys (such as int and float) to strings, and also recursively
    encodes all objects using Monty's as_dict() protocol.
    Args:
        obj: input json-like object.
        strict (bool): This parameters sets the behavior when jsanitize
            encounters an object it does not understand. If strict is True,
            jsanitize will try to get the as_dict() attribute of the object. If
            no such attribute is found, an attribute error will be thrown. If
            strict is False, jsanitize will simply call str(object) to convert
            the object to a string representation.
        allow_bson (bool): This parameters sets the behavior when jsanitize
            encounters an bson supported type such as objectid and datetime. If
            True, such bson types will be ignored, allowing for proper
            insertion into MongoDb databases.
    Returns:
        Sanitized dict that can be json serialized.
    """
    if allow_bson and (
        isinstance(obj, (datetime.datetime, bytes))
        or (bson is not None and isinstance(obj, bson.objectid.ObjectId))
    ):
        return obj
    if isinstance(obj, (list, tuple)):
        return [jsanitize(i, strict=strict, allow_bson=allow_bson) for i in obj]
    if np is not None and isinstance(obj, np.ndarray):
        return [
            jsanitize(i, strict=strict, allow_bson=allow_bson) for i in obj.tolist()
        ]
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {
            k.__str__(): jsanitize(v, strict=strict, allow_bson=allow_bson)
            for k, v in obj.items()
        }
    if isinstance(obj, MSONable):
        return {
            k.__str__(): jsanitize(v, strict=strict, allow_bson=allow_bson)
            for k, v in obj.as_dict().items()
        }

    if isinstance(obj, BaseModel):
        return {
            k.__str__(): jsanitize(v, strict=strict, allow_bson=allow_bson)
            for k, v in obj.dict().items()
        }
    if isinstance(obj, (int, float)):
        return obj

    if obj is None:
        return None

    if not strict:
        return obj.__str__()

    if isinstance(obj, str):
        return obj.__str__()

    return jsanitize(obj.as_dict(), strict=strict, allow_bson=allow_bson)


class ValueEnum(Enum):
    """
    Enum that serializes to string as the value
    """

    def __str__(self):
        return str(self.value)


class DocEnum(ValueEnum):
    """
    Enum with docstrings support
    from: https://stackoverflow.com/a/50473952
    """

    def __new__(cls, value, doc=None):
        """add docstring to the member of Enum if exists

        Args:
            value: Enum member value
            doc: Enum member docstring, None if not exists
        """
        self = object.__new__(cls)  # calling super().__new__(value) here would fail
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self

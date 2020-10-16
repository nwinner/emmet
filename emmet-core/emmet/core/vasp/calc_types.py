""" Module to define various calculation types as Enums for VASP """
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

_RUN_TYPE_DATA = loadfn(str(Path(__file__).parent.joinpath("run_types.yaml").resolve()))
_TASK_TYPES = [
    "NSCF Line",
    "NSCF Uniform",
    "Dielectric",
    "DFPT",
    "DFPT Dielectric",
    "NMR Nuclear Shielding",
    "NMR Electric Field Gradient",
    "Static",
    "Structure Optimization",
    "Deformation",
]

_RUN_TYPES = (
    [
        rt
        for functional_class in _RUN_TYPE_DATA
        for rt in _RUN_TYPE_DATA[functional_class]
    ]
    + [
        f"{rt}+U"
        for functional_class in _RUN_TYPE_DATA
        for rt in _RUN_TYPE_DATA[functional_class]
    ]
    + ["LDA", "LDA+U"]
)

RunType = Enum(  # type: ignore
    "RunType", dict({"_".join(rt.split()).replace("+", "_"): rt for rt in _RUN_TYPES})
)
RunType.__doc__ = "VASP calculation run types"

TaskType = Enum("TaskType", {"_".join(tt.split()): tt for tt in _TASK_TYPES})  # type: ignore
TaskType.__doc__ = "VASP calculation task types"

CalcType = Enum(  # type: ignore
    "CalcType",
    {
        f"{'_'.join(rt.split()).replace('+','_')}_{'_'.join(tt.split())}": f"{rt} {tt}"
        for rt, tt in product(_RUN_TYPES, _TASK_TYPES)
    },
)
CalcType.__doc__ = "VASP calculation types"


def run_type(parameters: Dict) -> RunType:
    """
    Determines the run_type from the VASP parameters dict
    This is adapted from pymatgen to be far less unstable

    Args:
        parameters: Dictionary of VASP parameters from Vasprun.xml
    """

    if parameters.get("LDAU", False):
        is_hubbard = "+U"
    else:
        is_hubbard = ""

    def _variant_equal(v1, v2) -> bool:
        """
        helper function to deal with strings
        """
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip().upper() == v2.strip().upper()
        else:
            return v1 == v2

    # This is to force an order of evaluation
    for functional_class in ["HF", "VDW", "METAGGA", "GGA"]:
        for special_type, params in _RUN_TYPE_DATA[functional_class].items():
            if all(
                [
                    _variant_equal(parameters.get(param, None), value)
                    for param, value in params.items()
                ]
            ):
                return RunType(f"{special_type}{is_hubbard}")

    return RunType(f"LDA{is_hubbard}")


def task_type(
    inputs: Dict[Literal["incar", "poscar", "kpoints", "potcar"], Dict]
) -> TaskType:
    """
    Determines the task type

    Args:
        inputs: inputs dict with an incar, kpoints, potcar, and poscar dictionaries
    """

    calc_type = []

    incar = inputs.get("incar", {})

    if incar.get("ICHARG", 0) > 10:
        try:
            kpts = inputs.get("kpoints") or {}
            kpt_labels = kpts.get("labels") or []
            num_kpt_labels = len(list(filter(None.__ne__, kpt_labels)))
        except Exception as e:
            raise Exception(
                "Couldn't identify total number of kpt labels: {}".format(e)
            )

        if num_kpt_labels > 0:
            calc_type.append("NSCF Line")
        else:
            calc_type.append("NSCF Uniform")

    elif incar.get("LEPSILON", False):
        if incar.get("IBRION", 0) > 6:
            calc_type.append("DFPT")
        calc_type.append("Dielectric")

    elif incar.get("IBRION", 0) > 6:
        calc_type.append("DFPT")

    elif incar.get("LCHIMAG", False):
        calc_type.append("NMR Nuclear Shielding")

    elif incar.get("LEFG", False):
        calc_type.append("NMR Electric Field Gradient")

    elif incar.get("NSW", 1) == 0:
        calc_type.append("Static")

    elif incar.get("ISIF", 2) == 3 and incar.get("IBRION", 0) > 0:
        calc_type.append("Structure Optimization")

    elif incar.get("ISIF", 3) == 2 and incar.get("IBRION", 0) > 0:
        calc_type.append("Deformation")

    return TaskType(" ".join(calc_type))


def calc_type(
    inputs: Dict[Literal["incar", "poscar", "kpoints", "potcar"], Dict],
    parameters: Dict,
) -> CalcType:
    """
    Determines the calc type

    Args:
        inputs: inputs dict with an incar, kpoints, potcar, and poscar dictionaries
        parameters: Dictionary of VASP parameters from Vasprun.xml
    """
    rt = run_type(parameters)
    tt = task_type(inputs)
    return CalcType(f"{rt} {tt}")

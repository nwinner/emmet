""" Module to define various calculation types as Enums for CP2K """
from pathlib import Path
from typing import Dict
from monty.serialization import loadfn


from emmet.core.cp2k.calc_types.enums import RunType, TaskType, CalcType

_RUN_TYPE_DATA = loadfn(str(Path(__file__).parent.joinpath("run_types.yaml").resolve()))


def run_type(dft: Dict) -> RunType:
    """
    Determines the run_type from the CP2K input dict
    This is adapted from pymatgen to be far less unstable

    Args:
        dft: dictionary of dft parameters (standard from task doc)
    """

    def _variant_equal(v1, v2) -> bool:
        """
        helper function to deal with strings
        """
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip().upper() == v2.strip().upper()
        else:
            return v1 == v2

    is_hubbard = '+U' if dft.get('dft_plus_u') else ''

    parameters = {
        'FUNCTIONAL': dft.get('functional'),
        'INTERACTION_POTENTIAL': dft.get('hfx', {}).get('Interaction_Potential'),
        'FRACTION': dft.get('hfx', {}).get('FRACTION', 0)
    }

    # Standard calc will only have one functional. If there are multiple functionals
    # used this is either a hybrid calc or a non-generic mixed calculation.
    if len(parameters['FUNCTIONAL']) == 1:
        parameters['FUNCTIONAL'] = parameters['FUNCTIONAL'][0]

    # If all parameters in for the functional_class.special_type located in
    # run_types.yaml are met, then that is the run type.
    for functional_class in _RUN_TYPE_DATA:
        for special_type, params in _RUN_TYPE_DATA[functional_class].items():
            if all(
                [
                    _variant_equal(parameters.get(param, None), value)
                    for param, value in params.items()
                ]
            ):
                return RunType(f"{functional_class}{is_hubbard}")


def task_type(
    inputs: Dict
) -> TaskType:
    """
    Determines the task type

    Args:
        inputs
    """

    calc_type = []

    cp2k_run_type = inputs.get('Run_type', '')

    if cp2k_run_type.upper() in ['ENERGY', 'ENERGY_FORCE', 'WAVEFUNCTION_OPTIMIZATION', 'WFN_OPT']:
        calc_type.append('Static')

    elif cp2k_run_type.upper() in ['GEO_OPT', 'GEOMETRY_OPTIMIZATION', 'CELL_OPT']:
        calc_type.append('Structure Optimization')

    elif cp2k_run_type.upper() in ['BAND']:
        calc_type.append('Band')

    elif cp2k_run_type.upper() in ['MOLECULAR_DYNAMICS', 'MD']:
        calc_type.append('Molecular Dynamics')

    elif cp2k_run_type.upper() in ['MONTE_CARLO', 'MC', 'TMC', 'TAMC']:
        calc_type.append('Monte Carlo')

    elif cp2k_run_type.upper() in ['LINEAR_RESPONSE', 'LR']:
        calc_type.append('Linear Response')

    elif cp2k_run_type.upper() in ['VIBRATIONAL_ANALYSIS', 'NORMAL_MODES']:
        calc_type.append('Vibrational Analysis')

    elif cp2k_run_type.upper() in ['ELECTRONIC_SPECTRA', 'SPECTRA']:
        calc_type.append('Electronic Spectra')

    elif cp2k_run_type.upper() in ['NEGF']:
        calc_type.append('Non-equilibrium Green\'s Function')

    elif cp2k_run_type.upper() in ['PINT', 'DRIVER']:
        calc_type.append('Path Integral')

    elif cp2k_run_type.upper() in ['RT_PROPAGATION', 'EHRENFEST_DYN']:
        calc_type.append('Real-time propagation')

    elif cp2k_run_type.upper() in ['BSSE']:
        calc_type.append('Base set superposition error')

    elif cp2k_run_type.upper() in ['DEBUG']:
        calc_type.append('Debug analysis')

    elif cp2k_run_type.upper() in ['NONE']:
        calc_type.append('None')

    return TaskType(" ".join(calc_type))


def calc_type(
    inputs: Dict,
) -> CalcType:
    """
    Determines the calc type

    Args:
        inputs: inputs dict with an incar, kpoints, potcar, and poscar dictionaries
        parameters: Dictionary of VASP parameters from Vasprun.xml
    """
    rt = run_type(inputs).value
    tt = task_type(inputs).value
    return CalcType(f"{rt} {tt}")

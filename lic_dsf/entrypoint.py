from __future__ import annotations

from .inputs import DEFAULT_INPUTS
from .internals import EvalContext, xl_cell, _FORMULAS
import warnings


def make_context(inputs=None):
    """Create an EvalContext with merged inputs."""
    merged = dict(DEFAULT_INPUTS)
    if inputs is not None:
        merged.update(inputs)
    return EvalContext(inputs=merged, formulas=_FORMULAS)


TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO = [
    'B1_GDP_ext!C35',
    'B1_GDP_ext!D35',
    'B1_GDP_ext!E35',
    'B1_GDP_ext!F35',
    'B1_GDP_ext!G35',
    'B1_GDP_ext!H35',
    'B1_GDP_ext!I35',
    'B1_GDP_ext!J35',
    'B1_GDP_ext!K35',
    'B1_GDP_ext!L35',
    'B1_GDP_ext!M35',
    'B1_GDP_ext!N35',
    'B1_GDP_ext!O35',
    'B1_GDP_ext!P35',
    'B1_GDP_ext!Q35',
    'B1_GDP_ext!R35',
    'B1_GDP_ext!S35',
    'B1_GDP_ext!T35',
    'B1_GDP_ext!U35',
    'B1_GDP_ext!V35',
    'B1_GDP_ext!W35',
    'B1_GDP_ext!X35',
]


def compute_pv_of_ppg_external_debt_to_gdp_ratio(inputs=None, *, ctx=None):
    """Compute pv_of_ppg_external_debt_to_gdp_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO}


TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO = [
    'B1_GDP_ext!C36',
    'B1_GDP_ext!D36',
    'B1_GDP_ext!E36',
    'B1_GDP_ext!F36',
    'B1_GDP_ext!G36',
    'B1_GDP_ext!H36',
    'B1_GDP_ext!I36',
    'B1_GDP_ext!J36',
    'B1_GDP_ext!K36',
    'B1_GDP_ext!L36',
    'B1_GDP_ext!M36',
    'B1_GDP_ext!N36',
    'B1_GDP_ext!O36',
    'B1_GDP_ext!P36',
    'B1_GDP_ext!Q36',
    'B1_GDP_ext!R36',
    'B1_GDP_ext!S36',
    'B1_GDP_ext!T36',
    'B1_GDP_ext!U36',
    'B1_GDP_ext!V36',
    'B1_GDP_ext!W36',
    'B1_GDP_ext!X36',
]


def compute_pv_of_ppg_external_debt_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute pv_of_ppg_external_debt_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO}


TARGETS_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO = [
    'B1_GDP_ext!C39',
    'B1_GDP_ext!D39',
    'B1_GDP_ext!E39',
    'B1_GDP_ext!F39',
    'B1_GDP_ext!G39',
    'B1_GDP_ext!H39',
    'B1_GDP_ext!I39',
    'B1_GDP_ext!J39',
    'B1_GDP_ext!K39',
    'B1_GDP_ext!L39',
    'B1_GDP_ext!M39',
    'B1_GDP_ext!N39',
    'B1_GDP_ext!O39',
    'B1_GDP_ext!P39',
    'B1_GDP_ext!Q39',
    'B1_GDP_ext!R39',
    'B1_GDP_ext!S39',
    'B1_GDP_ext!T39',
    'B1_GDP_ext!U39',
    'B1_GDP_ext!V39',
    'B1_GDP_ext!W39',
    'B1_GDP_ext!X39',
]


def compute_ppg_debt_service_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute ppg_debt_service_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO}


TARGETS_PPG_DEBT_SERVICE_TO_REVENUE_RATIO = [
    'B1_GDP_ext!C40',
    'B1_GDP_ext!D40',
    'B1_GDP_ext!E40',
    'B1_GDP_ext!F40',
    'B1_GDP_ext!G40',
    'B1_GDP_ext!H40',
    'B1_GDP_ext!I40',
    'B1_GDP_ext!J40',
    'B1_GDP_ext!K40',
    'B1_GDP_ext!L40',
    'B1_GDP_ext!M40',
    'B1_GDP_ext!N40',
    'B1_GDP_ext!O40',
    'B1_GDP_ext!P40',
    'B1_GDP_ext!Q40',
    'B1_GDP_ext!R40',
    'B1_GDP_ext!S40',
    'B1_GDP_ext!T40',
    'B1_GDP_ext!U40',
    'B1_GDP_ext!V40',
    'B1_GDP_ext!W40',
    'B1_GDP_ext!X40',
]


def compute_ppg_debt_service_to_revenue_ratio(inputs=None, *, ctx=None):
    """Compute ppg_debt_service_to_revenue_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PPG_DEBT_SERVICE_TO_REVENUE_RATIO}


TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO_2 = [
    'B3_Exports_ext!C35',
    'B3_Exports_ext!D35',
    'B3_Exports_ext!E35',
    'B3_Exports_ext!F35',
    'B3_Exports_ext!G35',
    'B3_Exports_ext!H35',
    'B3_Exports_ext!I35',
    'B3_Exports_ext!J35',
    'B3_Exports_ext!K35',
    'B3_Exports_ext!L35',
    'B3_Exports_ext!M35',
    'B3_Exports_ext!N35',
    'B3_Exports_ext!O35',
    'B3_Exports_ext!P35',
    'B3_Exports_ext!Q35',
    'B3_Exports_ext!R35',
    'B3_Exports_ext!S35',
    'B3_Exports_ext!T35',
    'B3_Exports_ext!U35',
    'B3_Exports_ext!V35',
    'B3_Exports_ext!W35',
    'B3_Exports_ext!X35',
]


def compute_pv_of_ppg_external_debt_to_gdp_ratio_2(inputs=None, *, ctx=None):
    """Compute pv_of_ppg_external_debt_to_gdp_ratio_2 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO_2}


TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO_2 = [
    'B3_Exports_ext!C36',
    'B3_Exports_ext!D36',
    'B3_Exports_ext!E36',
    'B3_Exports_ext!F36',
    'B3_Exports_ext!G36',
    'B3_Exports_ext!H36',
    'B3_Exports_ext!I36',
    'B3_Exports_ext!J36',
    'B3_Exports_ext!K36',
    'B3_Exports_ext!L36',
    'B3_Exports_ext!M36',
    'B3_Exports_ext!N36',
    'B3_Exports_ext!O36',
    'B3_Exports_ext!P36',
    'B3_Exports_ext!Q36',
    'B3_Exports_ext!R36',
    'B3_Exports_ext!S36',
    'B3_Exports_ext!T36',
    'B3_Exports_ext!U36',
    'B3_Exports_ext!V36',
    'B3_Exports_ext!W36',
    'B3_Exports_ext!X36',
]


def compute_pv_of_ppg_external_debt_to_exports_ratio_2(inputs=None, *, ctx=None):
    """Compute pv_of_ppg_external_debt_to_exports_ratio_2 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO_2}


TARGETS_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO_2 = [
    'B3_Exports_ext!C39',
    'B3_Exports_ext!D39',
    'B3_Exports_ext!E39',
    'B3_Exports_ext!F39',
    'B3_Exports_ext!G39',
    'B3_Exports_ext!H39',
    'B3_Exports_ext!I39',
    'B3_Exports_ext!J39',
    'B3_Exports_ext!K39',
    'B3_Exports_ext!L39',
    'B3_Exports_ext!M39',
    'B3_Exports_ext!N39',
    'B3_Exports_ext!O39',
    'B3_Exports_ext!P39',
    'B3_Exports_ext!Q39',
    'B3_Exports_ext!R39',
    'B3_Exports_ext!S39',
    'B3_Exports_ext!T39',
    'B3_Exports_ext!U39',
    'B3_Exports_ext!V39',
    'B3_Exports_ext!W39',
    'B3_Exports_ext!X39',
]


def compute_ppg_debt_service_to_exports_ratio_2(inputs=None, *, ctx=None):
    """Compute ppg_debt_service_to_exports_ratio_2 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO_2}


TARGETS_PPG_DEBT_SERVICE_TO_REVENUE_RATIO_2 = [
    'B3_Exports_ext!C40',
    'B3_Exports_ext!D40',
    'B3_Exports_ext!E40',
    'B3_Exports_ext!F40',
    'B3_Exports_ext!G40',
    'B3_Exports_ext!H40',
    'B3_Exports_ext!I40',
    'B3_Exports_ext!J40',
    'B3_Exports_ext!K40',
    'B3_Exports_ext!L40',
    'B3_Exports_ext!M40',
    'B3_Exports_ext!N40',
    'B3_Exports_ext!O40',
    'B3_Exports_ext!P40',
    'B3_Exports_ext!Q40',
    'B3_Exports_ext!R40',
    'B3_Exports_ext!S40',
    'B3_Exports_ext!T40',
    'B3_Exports_ext!U40',
    'B3_Exports_ext!V40',
    'B3_Exports_ext!W40',
    'B3_Exports_ext!X40',
]


def compute_ppg_debt_service_to_revenue_ratio_2(inputs=None, *, ctx=None):
    """Compute ppg_debt_service_to_revenue_ratio_2 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PPG_DEBT_SERVICE_TO_REVENUE_RATIO_2}


TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO_3 = [
    "'B4_other flows_ext'!C35",
    "'B4_other flows_ext'!D35",
    "'B4_other flows_ext'!E35",
    "'B4_other flows_ext'!F35",
    "'B4_other flows_ext'!G35",
    "'B4_other flows_ext'!H35",
    "'B4_other flows_ext'!I35",
    "'B4_other flows_ext'!J35",
    "'B4_other flows_ext'!K35",
    "'B4_other flows_ext'!L35",
    "'B4_other flows_ext'!M35",
    "'B4_other flows_ext'!N35",
    "'B4_other flows_ext'!O35",
    "'B4_other flows_ext'!P35",
    "'B4_other flows_ext'!Q35",
    "'B4_other flows_ext'!R35",
    "'B4_other flows_ext'!S35",
    "'B4_other flows_ext'!T35",
    "'B4_other flows_ext'!U35",
    "'B4_other flows_ext'!V35",
    "'B4_other flows_ext'!W35",
    "'B4_other flows_ext'!X35",
]


def compute_pv_of_ppg_external_debt_to_gdp_ratio_3(inputs=None, *, ctx=None):
    """Compute pv_of_ppg_external_debt_to_gdp_ratio_3 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO_3}


TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO_3 = [
    "'B4_other flows_ext'!C36",
    "'B4_other flows_ext'!D36",
    "'B4_other flows_ext'!E36",
    "'B4_other flows_ext'!F36",
    "'B4_other flows_ext'!G36",
    "'B4_other flows_ext'!H36",
    "'B4_other flows_ext'!I36",
    "'B4_other flows_ext'!J36",
    "'B4_other flows_ext'!K36",
    "'B4_other flows_ext'!L36",
    "'B4_other flows_ext'!M36",
    "'B4_other flows_ext'!N36",
    "'B4_other flows_ext'!O36",
    "'B4_other flows_ext'!P36",
    "'B4_other flows_ext'!Q36",
    "'B4_other flows_ext'!R36",
    "'B4_other flows_ext'!S36",
    "'B4_other flows_ext'!T36",
    "'B4_other flows_ext'!U36",
    "'B4_other flows_ext'!V36",
    "'B4_other flows_ext'!W36",
    "'B4_other flows_ext'!X36",
]


def compute_pv_of_ppg_external_debt_to_exports_ratio_3(inputs=None, *, ctx=None):
    """Compute pv_of_ppg_external_debt_to_exports_ratio_3 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO_3}


TARGETS_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO_3 = [
    "'B4_other flows_ext'!C39",
    "'B4_other flows_ext'!D39",
    "'B4_other flows_ext'!E39",
    "'B4_other flows_ext'!F39",
    "'B4_other flows_ext'!G39",
    "'B4_other flows_ext'!H39",
    "'B4_other flows_ext'!I39",
    "'B4_other flows_ext'!J39",
    "'B4_other flows_ext'!K39",
    "'B4_other flows_ext'!L39",
    "'B4_other flows_ext'!M39",
    "'B4_other flows_ext'!N39",
    "'B4_other flows_ext'!O39",
    "'B4_other flows_ext'!P39",
    "'B4_other flows_ext'!Q39",
    "'B4_other flows_ext'!R39",
    "'B4_other flows_ext'!S39",
    "'B4_other flows_ext'!T39",
    "'B4_other flows_ext'!U39",
    "'B4_other flows_ext'!V39",
    "'B4_other flows_ext'!W39",
    "'B4_other flows_ext'!X39",
]


def compute_ppg_debt_service_to_exports_ratio_3(inputs=None, *, ctx=None):
    """Compute ppg_debt_service_to_exports_ratio_3 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO_3}


TARGETS_PPG_DEBT_SERVICE_TO_REVENUE_RATIO_3 = [
    "'B4_other flows_ext'!C40",
    "'B4_other flows_ext'!D40",
    "'B4_other flows_ext'!E40",
    "'B4_other flows_ext'!F40",
    "'B4_other flows_ext'!G40",
    "'B4_other flows_ext'!H40",
    "'B4_other flows_ext'!I40",
    "'B4_other flows_ext'!J40",
    "'B4_other flows_ext'!K40",
    "'B4_other flows_ext'!L40",
    "'B4_other flows_ext'!M40",
    "'B4_other flows_ext'!N40",
    "'B4_other flows_ext'!O40",
    "'B4_other flows_ext'!P40",
    "'B4_other flows_ext'!Q40",
    "'B4_other flows_ext'!R40",
    "'B4_other flows_ext'!S40",
    "'B4_other flows_ext'!T40",
    "'B4_other flows_ext'!U40",
    "'B4_other flows_ext'!V40",
    "'B4_other flows_ext'!W40",
    "'B4_other flows_ext'!X40",
]


def compute_ppg_debt_service_to_revenue_ratio_3(inputs=None, *, ctx=None):
    """Compute ppg_debt_service_to_revenue_ratio_3 target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS_PPG_DEBT_SERVICE_TO_REVENUE_RATIO_3}


TARGETS = [
    'B1_GDP_ext!C35',
    'B1_GDP_ext!D35',
    'B1_GDP_ext!E35',
    'B1_GDP_ext!F35',
    'B1_GDP_ext!G35',
    'B1_GDP_ext!H35',
    'B1_GDP_ext!I35',
    'B1_GDP_ext!J35',
    'B1_GDP_ext!K35',
    'B1_GDP_ext!L35',
    'B1_GDP_ext!M35',
    'B1_GDP_ext!N35',
    'B1_GDP_ext!O35',
    'B1_GDP_ext!P35',
    'B1_GDP_ext!Q35',
    'B1_GDP_ext!R35',
    'B1_GDP_ext!S35',
    'B1_GDP_ext!T35',
    'B1_GDP_ext!U35',
    'B1_GDP_ext!V35',
    'B1_GDP_ext!W35',
    'B1_GDP_ext!X35',
    'B1_GDP_ext!C36',
    'B1_GDP_ext!D36',
    'B1_GDP_ext!E36',
    'B1_GDP_ext!F36',
    'B1_GDP_ext!G36',
    'B1_GDP_ext!H36',
    'B1_GDP_ext!I36',
    'B1_GDP_ext!J36',
    'B1_GDP_ext!K36',
    'B1_GDP_ext!L36',
    'B1_GDP_ext!M36',
    'B1_GDP_ext!N36',
    'B1_GDP_ext!O36',
    'B1_GDP_ext!P36',
    'B1_GDP_ext!Q36',
    'B1_GDP_ext!R36',
    'B1_GDP_ext!S36',
    'B1_GDP_ext!T36',
    'B1_GDP_ext!U36',
    'B1_GDP_ext!V36',
    'B1_GDP_ext!W36',
    'B1_GDP_ext!X36',
    'B1_GDP_ext!C39',
    'B1_GDP_ext!D39',
    'B1_GDP_ext!E39',
    'B1_GDP_ext!F39',
    'B1_GDP_ext!G39',
    'B1_GDP_ext!H39',
    'B1_GDP_ext!I39',
    'B1_GDP_ext!J39',
    'B1_GDP_ext!K39',
    'B1_GDP_ext!L39',
    'B1_GDP_ext!M39',
    'B1_GDP_ext!N39',
    'B1_GDP_ext!O39',
    'B1_GDP_ext!P39',
    'B1_GDP_ext!Q39',
    'B1_GDP_ext!R39',
    'B1_GDP_ext!S39',
    'B1_GDP_ext!T39',
    'B1_GDP_ext!U39',
    'B1_GDP_ext!V39',
    'B1_GDP_ext!W39',
    'B1_GDP_ext!X39',
    'B1_GDP_ext!C40',
    'B1_GDP_ext!D40',
    'B1_GDP_ext!E40',
    'B1_GDP_ext!F40',
    'B1_GDP_ext!G40',
    'B1_GDP_ext!H40',
    'B1_GDP_ext!I40',
    'B1_GDP_ext!J40',
    'B1_GDP_ext!K40',
    'B1_GDP_ext!L40',
    'B1_GDP_ext!M40',
    'B1_GDP_ext!N40',
    'B1_GDP_ext!O40',
    'B1_GDP_ext!P40',
    'B1_GDP_ext!Q40',
    'B1_GDP_ext!R40',
    'B1_GDP_ext!S40',
    'B1_GDP_ext!T40',
    'B1_GDP_ext!U40',
    'B1_GDP_ext!V40',
    'B1_GDP_ext!W40',
    'B1_GDP_ext!X40',
    'B3_Exports_ext!C35',
    'B3_Exports_ext!D35',
    'B3_Exports_ext!E35',
    'B3_Exports_ext!F35',
    'B3_Exports_ext!G35',
    'B3_Exports_ext!H35',
    'B3_Exports_ext!I35',
    'B3_Exports_ext!J35',
    'B3_Exports_ext!K35',
    'B3_Exports_ext!L35',
    'B3_Exports_ext!M35',
    'B3_Exports_ext!N35',
    'B3_Exports_ext!O35',
    'B3_Exports_ext!P35',
    'B3_Exports_ext!Q35',
    'B3_Exports_ext!R35',
    'B3_Exports_ext!S35',
    'B3_Exports_ext!T35',
    'B3_Exports_ext!U35',
    'B3_Exports_ext!V35',
    'B3_Exports_ext!W35',
    'B3_Exports_ext!X35',
    'B3_Exports_ext!C36',
    'B3_Exports_ext!D36',
    'B3_Exports_ext!E36',
    'B3_Exports_ext!F36',
    'B3_Exports_ext!G36',
    'B3_Exports_ext!H36',
    'B3_Exports_ext!I36',
    'B3_Exports_ext!J36',
    'B3_Exports_ext!K36',
    'B3_Exports_ext!L36',
    'B3_Exports_ext!M36',
    'B3_Exports_ext!N36',
    'B3_Exports_ext!O36',
    'B3_Exports_ext!P36',
    'B3_Exports_ext!Q36',
    'B3_Exports_ext!R36',
    'B3_Exports_ext!S36',
    'B3_Exports_ext!T36',
    'B3_Exports_ext!U36',
    'B3_Exports_ext!V36',
    'B3_Exports_ext!W36',
    'B3_Exports_ext!X36',
    'B3_Exports_ext!C39',
    'B3_Exports_ext!D39',
    'B3_Exports_ext!E39',
    'B3_Exports_ext!F39',
    'B3_Exports_ext!G39',
    'B3_Exports_ext!H39',
    'B3_Exports_ext!I39',
    'B3_Exports_ext!J39',
    'B3_Exports_ext!K39',
    'B3_Exports_ext!L39',
    'B3_Exports_ext!M39',
    'B3_Exports_ext!N39',
    'B3_Exports_ext!O39',
    'B3_Exports_ext!P39',
    'B3_Exports_ext!Q39',
    'B3_Exports_ext!R39',
    'B3_Exports_ext!S39',
    'B3_Exports_ext!T39',
    'B3_Exports_ext!U39',
    'B3_Exports_ext!V39',
    'B3_Exports_ext!W39',
    'B3_Exports_ext!X39',
    'B3_Exports_ext!C40',
    'B3_Exports_ext!D40',
    'B3_Exports_ext!E40',
    'B3_Exports_ext!F40',
    'B3_Exports_ext!G40',
    'B3_Exports_ext!H40',
    'B3_Exports_ext!I40',
    'B3_Exports_ext!J40',
    'B3_Exports_ext!K40',
    'B3_Exports_ext!L40',
    'B3_Exports_ext!M40',
    'B3_Exports_ext!N40',
    'B3_Exports_ext!O40',
    'B3_Exports_ext!P40',
    'B3_Exports_ext!Q40',
    'B3_Exports_ext!R40',
    'B3_Exports_ext!S40',
    'B3_Exports_ext!T40',
    'B3_Exports_ext!U40',
    'B3_Exports_ext!V40',
    'B3_Exports_ext!W40',
    'B3_Exports_ext!X40',
    "'B4_other flows_ext'!C35",
    "'B4_other flows_ext'!D35",
    "'B4_other flows_ext'!E35",
    "'B4_other flows_ext'!F35",
    "'B4_other flows_ext'!G35",
    "'B4_other flows_ext'!H35",
    "'B4_other flows_ext'!I35",
    "'B4_other flows_ext'!J35",
    "'B4_other flows_ext'!K35",
    "'B4_other flows_ext'!L35",
    "'B4_other flows_ext'!M35",
    "'B4_other flows_ext'!N35",
    "'B4_other flows_ext'!O35",
    "'B4_other flows_ext'!P35",
    "'B4_other flows_ext'!Q35",
    "'B4_other flows_ext'!R35",
    "'B4_other flows_ext'!S35",
    "'B4_other flows_ext'!T35",
    "'B4_other flows_ext'!U35",
    "'B4_other flows_ext'!V35",
    "'B4_other flows_ext'!W35",
    "'B4_other flows_ext'!X35",
    "'B4_other flows_ext'!C36",
    "'B4_other flows_ext'!D36",
    "'B4_other flows_ext'!E36",
    "'B4_other flows_ext'!F36",
    "'B4_other flows_ext'!G36",
    "'B4_other flows_ext'!H36",
    "'B4_other flows_ext'!I36",
    "'B4_other flows_ext'!J36",
    "'B4_other flows_ext'!K36",
    "'B4_other flows_ext'!L36",
    "'B4_other flows_ext'!M36",
    "'B4_other flows_ext'!N36",
    "'B4_other flows_ext'!O36",
    "'B4_other flows_ext'!P36",
    "'B4_other flows_ext'!Q36",
    "'B4_other flows_ext'!R36",
    "'B4_other flows_ext'!S36",
    "'B4_other flows_ext'!T36",
    "'B4_other flows_ext'!U36",
    "'B4_other flows_ext'!V36",
    "'B4_other flows_ext'!W36",
    "'B4_other flows_ext'!X36",
    "'B4_other flows_ext'!C39",
    "'B4_other flows_ext'!D39",
    "'B4_other flows_ext'!E39",
    "'B4_other flows_ext'!F39",
    "'B4_other flows_ext'!G39",
    "'B4_other flows_ext'!H39",
    "'B4_other flows_ext'!I39",
    "'B4_other flows_ext'!J39",
    "'B4_other flows_ext'!K39",
    "'B4_other flows_ext'!L39",
    "'B4_other flows_ext'!M39",
    "'B4_other flows_ext'!N39",
    "'B4_other flows_ext'!O39",
    "'B4_other flows_ext'!P39",
    "'B4_other flows_ext'!Q39",
    "'B4_other flows_ext'!R39",
    "'B4_other flows_ext'!S39",
    "'B4_other flows_ext'!T39",
    "'B4_other flows_ext'!U39",
    "'B4_other flows_ext'!V39",
    "'B4_other flows_ext'!W39",
    "'B4_other flows_ext'!X39",
    "'B4_other flows_ext'!C40",
    "'B4_other flows_ext'!D40",
    "'B4_other flows_ext'!E40",
    "'B4_other flows_ext'!F40",
    "'B4_other flows_ext'!G40",
    "'B4_other flows_ext'!H40",
    "'B4_other flows_ext'!I40",
    "'B4_other flows_ext'!J40",
    "'B4_other flows_ext'!K40",
    "'B4_other flows_ext'!L40",
    "'B4_other flows_ext'!M40",
    "'B4_other flows_ext'!N40",
    "'B4_other flows_ext'!O40",
    "'B4_other flows_ext'!P40",
    "'B4_other flows_ext'!Q40",
    "'B4_other flows_ext'!R40",
    "'B4_other flows_ext'!S40",
    "'B4_other flows_ext'!T40",
    "'B4_other flows_ext'!U40",
    "'B4_other flows_ext'!V40",
    "'B4_other flows_ext'!W40",
    "'B4_other flows_ext'!X40",
]


def compute_all(inputs=None, *, ctx=None):
    """Compute all target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: xl_cell(ctx, target) for target in TARGETS}

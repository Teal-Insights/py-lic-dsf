from __future__ import annotations

from .inputs import DEFAULT_INPUTS
from .internals import EvalContext, xl_range, _FORMULAS
import warnings


def make_context(inputs=None):
    """Create an EvalContext with merged inputs."""
    merged = dict(DEFAULT_INPUTS)
    if inputs is not None:
        merged.update(inputs)
    return EvalContext(inputs=merged, formulas=_FORMULAS)


TARGETS_B1_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO = {
    'B1_GDP_ext!C35:B1_GDP_ext!X35': xl_range,
}


def compute_b1_pv_of_ppg_external_debt_to_gdp_ratio(inputs=None, *, ctx=None):
    """Compute b1_pv_of_ppg_external_debt_to_gdp_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B1_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO.items()}


TARGETS_B1_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO = {
    'B1_GDP_ext!C36:B1_GDP_ext!X36': xl_range,
}


def compute_b1_pv_of_ppg_external_debt_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute b1_pv_of_ppg_external_debt_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B1_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO.items()}


TARGETS_B1_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO = {
    'B1_GDP_ext!C39:B1_GDP_ext!X39': xl_range,
}


def compute_b1_ppg_debt_service_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute b1_ppg_debt_service_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B1_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO.items()}


TARGETS_B1_PPG_DEBT_SERVICE_TO_REVENUE_RATIO = {
    'B1_GDP_ext!C40:B1_GDP_ext!X40': xl_range,
}


def compute_b1_ppg_debt_service_to_revenue_ratio(inputs=None, *, ctx=None):
    """Compute b1_ppg_debt_service_to_revenue_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B1_PPG_DEBT_SERVICE_TO_REVENUE_RATIO.items()}


TARGETS_B3_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO = {
    'B3_Exports_ext!C35:B3_Exports_ext!X35': xl_range,
}


def compute_b3_pv_of_ppg_external_debt_to_gdp_ratio(inputs=None, *, ctx=None):
    """Compute b3_pv_of_ppg_external_debt_to_gdp_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B3_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO.items()}


TARGETS_B3_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO = {
    'B3_Exports_ext!C36:B3_Exports_ext!X36': xl_range,
}


def compute_b3_pv_of_ppg_external_debt_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute b3_pv_of_ppg_external_debt_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B3_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO.items()}


TARGETS_B3_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO = {
    'B3_Exports_ext!C39:B3_Exports_ext!X39': xl_range,
}


def compute_b3_ppg_debt_service_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute b3_ppg_debt_service_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B3_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO.items()}


TARGETS_B3_PPG_DEBT_SERVICE_TO_REVENUE_RATIO = {
    'B3_Exports_ext!C40:B3_Exports_ext!X40': xl_range,
}


def compute_b3_ppg_debt_service_to_revenue_ratio(inputs=None, *, ctx=None):
    """Compute b3_ppg_debt_service_to_revenue_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B3_PPG_DEBT_SERVICE_TO_REVENUE_RATIO.items()}


TARGETS_B4_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO = {
    "'B4_other flows_ext'!C35:'B4_other flows_ext'!X35": xl_range,
}


def compute_b4_pv_of_ppg_external_debt_to_gdp_ratio(inputs=None, *, ctx=None):
    """Compute b4_pv_of_ppg_external_debt_to_gdp_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B4_PV_OF_PPG_EXTERNAL_DEBT_TO_GDP_RATIO.items()}


TARGETS_B4_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO = {
    "'B4_other flows_ext'!C36:'B4_other flows_ext'!X36": xl_range,
}


def compute_b4_pv_of_ppg_external_debt_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute b4_pv_of_ppg_external_debt_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B4_PV_OF_PPG_EXTERNAL_DEBT_TO_EXPORTS_RATIO.items()}


TARGETS_B4_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO = {
    "'B4_other flows_ext'!C39:'B4_other flows_ext'!X39": xl_range,
}


def compute_b4_ppg_debt_service_to_exports_ratio(inputs=None, *, ctx=None):
    """Compute b4_ppg_debt_service_to_exports_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B4_PPG_DEBT_SERVICE_TO_EXPORTS_RATIO.items()}


TARGETS_B4_PPG_DEBT_SERVICE_TO_REVENUE_RATIO = {
    "'B4_other flows_ext'!C40:'B4_other flows_ext'!X40": xl_range,
}


def compute_b4_ppg_debt_service_to_revenue_ratio(inputs=None, *, ctx=None):
    """Compute b4_ppg_debt_service_to_revenue_ratio target cells and return results."""
    if ctx is None:
        ctx = make_context(inputs)
    elif inputs is not None:
        warnings.warn(
            "inputs will be ignored because ctx was provided",
            UserWarning,
            stacklevel=2,
        )
    return {target: handler(ctx, target) for target, handler in TARGETS_B4_PPG_DEBT_SERVICE_TO_REVENUE_RATIO.items()}


TARGETS = {
    "'B4_other flows_ext'!C35:'B4_other flows_ext'!X35": xl_range,
    "'B4_other flows_ext'!C36:'B4_other flows_ext'!X36": xl_range,
    "'B4_other flows_ext'!C39:'B4_other flows_ext'!X39": xl_range,
    "'B4_other flows_ext'!C40:'B4_other flows_ext'!X40": xl_range,
    'B1_GDP_ext!C35:B1_GDP_ext!X35': xl_range,
    'B1_GDP_ext!C36:B1_GDP_ext!X36': xl_range,
    'B1_GDP_ext!C39:B1_GDP_ext!X39': xl_range,
    'B1_GDP_ext!C40:B1_GDP_ext!X40': xl_range,
    'B3_Exports_ext!C35:B3_Exports_ext!X35': xl_range,
    'B3_Exports_ext!C36:B3_Exports_ext!X36': xl_range,
    'B3_Exports_ext!C39:B3_Exports_ext!X39': xl_range,
    'B3_Exports_ext!C40:B3_Exports_ext!X40': xl_range,
}


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
    return {target: handler(ctx, target) for target, handler in TARGETS.items()}

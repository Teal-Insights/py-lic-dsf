"""Named Excel cell-overlay presets for parity cases (Phase C).

Presets expand to :class:`~tests.parity.case_schema.CellOverlay` tuples.
User-column cells follow ``_prefer_user`` conventions in the loaders
(Input 6 standard: column D; tailored: column H).

For Input 6 standard shocks, presets write **both** the standalone shock cell
and the matching B6 combo cell so Excel and Python stay aligned (Excel's B6
block often tracks the standalone size when the user edits column D).
"""

from __future__ import annotations

from tests.parity.case_schema import CellOverlay

_INPUT6 = "Input 6(optional)-Standard Test"
_TAILORED = "Input 6 - Tailored Tests"
_INPUT1 = "Input 1 - Basics"
_INPUT2 = "Input 2 - Debt Coverage"
_INPUT7 = "Input 7 - Residual Financing"

# Template Input 7 public residual shares (lic-dsf-template-2025-08-12).
_TEMPLATE_RESFIN_DOM_MLT = 0.2275655436226405
# Template Input 2 F21:F24 contingent-liability components (% of GDP).
# Excel C1 reads these rows (AA62:AA65), not F25 alone.
_TEMPLATE_CL_F21 = 0.0
_TEMPLATE_CL_F22 = 2.0
_TEMPLATE_CL_F23 = 2.375480101740474
_TEMPLATE_CL_F24 = 5.0
_TEMPLATE_CL_PCT_GDP = (
    _TEMPLATE_CL_F21 + _TEMPLATE_CL_F22 + _TEMPLATE_CL_F23 + _TEMPLATE_CL_F24
)


def _input6_shock(*, standalone: str, combo: str, value: float) -> tuple[CellOverlay, ...]:
    """Write default (C) + user (D) for standalone and combo shock rows."""
    out: list[CellOverlay] = []
    for cell in (standalone, combo):
        # C and D: cover formulas that read either column.
        col_letter = cell[0]
        row = cell[1:]
        if col_letter != "D":
            raise ValueError(f"expected D-column user cell, got {cell}")
        out.append(CellOverlay(sheet=_INPUT6, cell=f"C{row}", value=value))
        out.append(CellOverlay(sheet=_INPUT6, cell=f"D{row}", value=value))
    return tuple(out)


_PRESETS: dict[str, tuple[CellOverlay, ...]] = {
    "higher_fx_shock": _input6_shock(standalone="D38", combo="D58", value=50.0),
    "larger_gdp_shock": _input6_shock(standalone="D17", combo="D41", value=2.0),
    "larger_exports_shock": _input6_shock(standalone="D25", combo="D44", value=2.0),
    "larger_primary_balance_shock": _input6_shock(
        standalone="D21", combo="D47", value=2.0
    ),
    "larger_transfers_shock": _input6_shock(
        standalone="D29", combo="D50", value=2.0
    ),
    "larger_fdi_shock": _input6_shock(standalone="D32", combo="D53", value=2.0),
    "interactions_off": (
        CellOverlay(sheet=_INPUT6, cell="C8", value="Off"),
    ),
    "weaker_fx_passthrough": (
        CellOverlay(sheet=_INPUT6, cell="G36", value=0.1),
        CellOverlay(sheet=_INPUT6, cell="H36", value=0.1),
    ),
    "higher_inflation_elasticity": (
        CellOverlay(sheet=_INPUT6, cell="G17", value=1.0),
        CellOverlay(sheet=_INPUT6, cell="H17", value=1.0),
    ),
    "higher_exports_gdp_elasticity": (
        CellOverlay(sheet=_INPUT6, cell="G25", value=1.2),
        CellOverlay(sheet=_INPUT6, cell="H25", value=1.2),
    ),
    "market_access_off": (
        CellOverlay(sheet=_INPUT1, cell="C27", value="No"),
    ),
    "higher_market_cost": (
        CellOverlay(sheet=_TAILORED, cell="G52", value=600.0),
        CellOverlay(sheet=_TAILORED, cell="H52", value=600.0),
    ),
    "higher_market_fx": (
        CellOverlay(sheet=_TAILORED, cell="G58", value=25.0),
        CellOverlay(sheet=_TAILORED, cell="H58", value=25.0),
    ),
    "natural_disaster_on": (
        CellOverlay(sheet=_TAILORED, cell="C9", value="Yes"),
        CellOverlay(sheet=_TAILORED, cell="G21", value=15.0),
        CellOverlay(sheet=_TAILORED, cell="H21", value=15.0),
    ),
    # Raise CL shock to 1.5× template. Excel C1 uses F21:F24 (AA62:AA65);
    # F25 is the SUM used by the Python loader.
    "larger_cl_shock": (
        CellOverlay(sheet=_INPUT2, cell="F21", value=_TEMPLATE_CL_F21 * 1.5),
        CellOverlay(sheet=_INPUT2, cell="F22", value=_TEMPLATE_CL_F22 * 1.5),
        CellOverlay(sheet=_INPUT2, cell="F23", value=_TEMPLATE_CL_F23 * 1.5),
        CellOverlay(sheet=_INPUT2, cell="F24", value=_TEMPLATE_CL_F24 * 1.5),
        CellOverlay(
            sheet=_INPUT2,
            cell="F25",
            value=_TEMPLATE_CL_PCT_GDP * 1.5,
        ),
    ),
    # Raise external MLT share; residualize ST so H/J11 match Excel I11=1−I9−I10
    # with the template domestic-MLT share left unchanged.
    "higher_resfin_external_share": (
        CellOverlay(sheet=_INPUT7, cell="H9", value=0.7),
        CellOverlay(sheet=_INPUT7, cell="J9", value=0.7),
        CellOverlay(
            sheet=_INPUT7,
            cell="H11",
            value=1.0 - 0.7 - _TEMPLATE_RESFIN_DOM_MLT,
        ),
        CellOverlay(
            sheet=_INPUT7,
            cell="J11",
            value=1.0 - 0.7 - _TEMPLATE_RESFIN_DOM_MLT,
        ),
    ),
    # Raise domestic ST share to 0.50; residualize external MLT so shares sum
    # to 1 with template domestic-MLT left unchanged (Excel I11=1−I9−I10).
    "higher_resfin_domestic_st_share": (
        CellOverlay(
            sheet=_INPUT7,
            cell="H9",
            value=1.0 - 0.50 - _TEMPLATE_RESFIN_DOM_MLT,
        ),
        CellOverlay(
            sheet=_INPUT7,
            cell="J9",
            value=1.0 - 0.50 - _TEMPLATE_RESFIN_DOM_MLT,
        ),
        CellOverlay(sheet=_INPUT7, cell="H11", value=0.50),
        CellOverlay(sheet=_INPUT7, cell="J11", value=0.50),
    ),
}


def known_presets() -> tuple[str, ...]:
    """Return registered preset names."""
    return tuple(sorted(_PRESETS))


def expand_presets(names: tuple[str, ...] | list[str]) -> tuple[CellOverlay, ...]:
    """Expand named presets into overlays; unknown names raise ``KeyError``."""
    overlays: list[CellOverlay] = []
    for name in names:
        if name not in _PRESETS:
            raise KeyError(
                f"unknown overlay preset {name!r}; known: {known_presets()}"
            )
        overlays.extend(_PRESETS[name])
    return tuple(overlays)

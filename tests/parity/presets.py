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
# Template commodity fuel/nonfuel shares and nonfuel price (lic-dsf-template).
_TEMPLATE_FUEL_SHARE = 0.09120308550958045
_TEMPLATE_NONFUEL_SHARE = 0.41663011382797605
_TEMPLATE_NONFUEL_PRICE = -0.2168778144226342
_FUEL_SEVERE_PRICE = -0.50
_FUEL_SEVERE_AVG = (
    (_FUEL_SEVERE_PRICE * _TEMPLATE_FUEL_SHARE)
    + (_TEMPLATE_NONFUEL_PRICE * _TEMPLATE_NONFUEL_SHARE)
) / (_TEMPLATE_FUEL_SHARE + _TEMPLATE_NONFUEL_SHARE)


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
    # Standalone GDP=2 SD; combo left at Excel's natural half (D41=D17/2 → 1).
    # Contrasts with larger_gdp_shock which dual-writes the full 2 into combo.
    "larger_gdp_shock_standalone_only": (
        CellOverlay(sheet=_INPUT6, cell="C17", value=2.0),
        CellOverlay(sheet=_INPUT6, cell="D17", value=2.0),
        CellOverlay(sheet=_INPUT6, cell="C41", value=1.0),
        CellOverlay(sheet=_INPUT6, cell="D41", value=1.0),
    ),
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
    # C4 FX deflator passthrough (Tailored K58/L58 → C4!AB23), not Input 6 G36.
    "weaker_market_fx_passthrough": (
        CellOverlay(sheet=_TAILORED, cell="K58", value=0.1),
        CellOverlay(sheet=_TAILORED, cell="L58", value=0.1),
    ),
    "shorter_market_maturity_cap": (
        CellOverlay(sheet=_TAILORED, cell="G54", value=3.0),
        CellOverlay(sheet=_TAILORED, cell="H54", value=3.0),
    ),
    # G46/H46 average price shock. Excel K26/L26 and K27/L27 are formulas of
    # G46 (×0.5/-10% and ×0.75/-10%); write them too so data_only caches match.
    "more_severe_commodity_price": (
        CellOverlay(sheet=_TAILORED, cell="G46", value=-0.40),
        CellOverlay(sheet=_TAILORED, cell="H46", value=-0.40),
        CellOverlay(sheet=_TAILORED, cell="K26", value=-0.40 * 0.5 / -0.10),
        CellOverlay(sheet=_TAILORED, cell="L26", value=-0.40 * 0.5 / -0.10),
        CellOverlay(sheet=_TAILORED, cell="K27", value=-0.40 * 0.75 / -0.10),
        CellOverlay(sheet=_TAILORED, cell="L27", value=-0.40 * 0.75 / -0.10),
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
    # Input 7 E14 = IF(ISNUMBER(D14),D14,C14). Write C+D+E so loaders that
    # read E14 under data_only=True do not see a stale ~8% cache.
    "higher_resfin_external_interest": (
        CellOverlay(sheet=_INPUT7, cell="C14", value=0.12),
        CellOverlay(sheet=_INPUT7, cell="D14", value=0.12),
        CellOverlay(sheet=_INPUT7, cell="E14", value=0.12),
    ),
    # E16 = IF(ISNUMBER(D16),D16,C16); write C+D+E (years).
    "longer_resfin_maturity": (
        CellOverlay(sheet=_INPUT7, cell="C16", value=12),
        CellOverlay(sheet=_INPUT7, cell="D16", value=12),
        CellOverlay(sheet=_INPUT7, cell="E16", value=12),
    ),
    # E15 discount (decimal). Write C+D+E.
    "higher_resfin_discount": (
        CellOverlay(sheet=_INPUT7, cell="C15", value=0.07),
        CellOverlay(sheet=_INPUT7, cell="D15", value=0.07),
        CellOverlay(sheet=_INPUT7, cell="E15", value=0.07),
    ),
    # E17 grace years. Write C+D+E.
    "longer_resfin_grace": (
        CellOverlay(sheet=_INPUT7, cell="C17", value=6),
        CellOverlay(sheet=_INPUT7, cell="D17", value=6),
        CellOverlay(sheet=_INPUT7, cell="E17", value=6),
    ),
    # Domestic MLT real rate (H/I/J19). Raise ≈2.9% → 6%.
    "higher_resfin_domestic_mlt_rate": (
        CellOverlay(sheet=_INPUT7, cell="H19", value=0.06),
        CellOverlay(sheet=_INPUT7, cell="I19", value=0.06),
        CellOverlay(sheet=_INPUT7, cell="J19", value=0.06),
    ),
    # T2: larger disaster shock with flag forced Yes (template C9 is formula).
    "larger_disaster_shock": (
        CellOverlay(sheet=_TAILORED, cell="C9", value="Yes"),
        CellOverlay(sheet=_TAILORED, cell="G21", value=20.0),
        CellOverlay(sheet=_TAILORED, cell="H21", value=20.0),
    ),
    # C4 grace shorten factor (Input 6 G56/H56); default 2/3 → 0.5.
    "lower_market_grace_factor": (
        CellOverlay(sheet=_TAILORED, cell="G56", value=0.5),
        CellOverlay(sheet=_TAILORED, cell="H56", value=0.5),
    ),
    # Fuel price more severe; rewrite G46/H46 + K26/L26/K27/L27 from the
    # Excel G46 weighted-average identity so data_only caches match grapher.
    "more_severe_fuel_price": (
        CellOverlay(sheet=_TAILORED, cell="G32", value=-0.50),
        CellOverlay(sheet=_TAILORED, cell="H32", value=-0.50),
        # shares/nonfuel left at template; avg recomputed in expand below — use
        # constants matching template fuel/nonfuel shares at mint time.
        # Template: sf≈0.091203, sn≈0.416630, pn≈-0.216878
        # avg = ( -0.50*sf + pn*sn ) / (sf+sn)
        CellOverlay(sheet=_TAILORED, cell="G46", value=_FUEL_SEVERE_AVG),
        CellOverlay(sheet=_TAILORED, cell="H46", value=_FUEL_SEVERE_AVG),
        CellOverlay(
            sheet=_TAILORED,
            cell="K26",
            value=_FUEL_SEVERE_AVG * 0.5 / -0.10,
        ),
        CellOverlay(
            sheet=_TAILORED,
            cell="L26",
            value=_FUEL_SEVERE_AVG * 0.5 / -0.10,
        ),
        CellOverlay(
            sheet=_TAILORED,
            cell="K27",
            value=_FUEL_SEVERE_AVG * 0.75 / -0.10,
        ),
        CellOverlay(
            sheet=_TAILORED,
            cell="L27",
            value=_FUEL_SEVERE_AVG * 0.75 / -0.10,
        ),
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

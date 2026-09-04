"""Public stress ratio projections (Output 3-2 + Output 3-1 B2)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.market_access import (
    _amortizing_stock_from_disbursements,
    _market_add_int_interest_parts,
    _market_add_int_rates,
    _shock_window_years,
)
from lic_dsf.stress.path import ShockedMacroPath, ShockMetadata, projection_shock_window
from lic_dsf.stress.public_gfn import (
    PublicGFNIdentity,
    _a1_primary_deficit_lcu,
    _a1_public_gdp_lcu,
    _align,
    _b1_other_identified_flows_lcu,
    _b1_primary_deficit_lcu,
    _b1_public_gdp_lcu,
    _clamp_nonnegative,
    _fx_shock_projection_year,
    _growth_pct,
    _pct,
    _public_real_and_lcu_deflator,
    estimate_b1_public_gfn,
)
from lic_dsf.stress.ratios.public_paths import (
    _b5_public_fx_eop_for_debt_service,
    _combo_primary_deficit_lcu,
    _public_domestic_st_lcu_path,
    _public_existing_debt_service_parts_lcu,
    _public_external_face_lcu_path,
    _public_external_pv_lcu_path,
)
from lic_dsf.stress.residual_pv import PublicResFinOverlay
from lic_dsf.stress.types import Input6StandardParams, ThresholdRule


@dataclass(slots=True)
class StressPublicRatios:
    """Public DSA ratios under stress (no shock / gap iteration logic).

    Public methods feed Output 3-2. External-facing methods feed Output 3-1 B2
    (Chart Data wires B2 from the public B2 sheet, not an external B2 book).
    """

    path: ShockedMacroPath
    external: ExternalDebtBook
    resfin: PublicResFinOverlay
    inflation_elasticity: float = 0.0
    fx_passthrough: float = 0.0
    market_access: bool = False
    resfin_external_ds: PublicResFinOverlay | None = None
    gfn: PublicGFNIdentity | None = None
    scenario_id: str = "B1_GDP_pub"
    # Explicit combo flag for legacy StressPublicBook construction (B6).
    # When None, derived from path.metadata (exports + FX depreciation).
    _combo_primary_override: bool | None = None
    _debt_to_gdp_cache: pd.Series | None = None
    _gdp_lcu_cache: pd.Series | None = None
    _external_face_cache: pd.Series | None = None
    _external_pv_cache: pd.Series | None = None
    _domestic_st_cache: pd.Series | None = None
    _domestic_face_cache: pd.Series | None = None

    @classmethod
    def from_path(
        cls,
        path: ShockedMacroPath,
        external: ExternalDebtBook,
        resfin: PublicResFinOverlay,
        *,
        inflation_elasticity: float = 0.0,
        fx_passthrough: float = 0.0,
        market_access: bool = False,
        resfin_external_ds: PublicResFinOverlay | None = None,
        gfn: PublicGFNIdentity | None = None,
        scenario_id: str = "B1_GDP_pub",
    ) -> StressPublicRatios:
        """Build ratios from a shocked path and public ResFin overlay."""
        return cls(
            path=path,
            external=external,
            resfin=resfin,
            inflation_elasticity=float(inflation_elasticity),
            fx_passthrough=float(fx_passthrough),
            market_access=bool(market_access),
            resfin_external_ds=resfin_external_ds,
            gfn=gfn,
            scenario_id=scenario_id,
        )

    @classmethod
    def from_legacy_fields(
        cls,
        *,
        macro: MacroDebtBook,
        external: ExternalDebtBook,
        baseline_macro: MacroDebtBook,
        resfin: PublicResFinOverlay,
        scenario_id: str = "B1_GDP_pub",
        inflation_elasticity: float = 0.0,
        market_access: bool = False,
        fx_passthrough: float = 0.0,
        fx_depreciation_pct: float = 0.0,
        combo_primary: bool = False,
        input6: Input6StandardParams | None = None,
        gdp_lcu_override: pd.Series | None = None,
        resfin_external_ds: PublicResFinOverlay | None = None,
        external_dsa_borrowing_usd: pd.Series | None = None,
        primary_exp_gdp_denominator: pd.Series | None = None,
        lcu_deflator_growth: pd.Series | None = None,
    ) -> StressPublicRatios:
        """Build ratios from legacy ``StressPublicBook`` constructor fields."""
        years = macro.inputs.years
        first = macro.inputs.first_projection_year
        try:
            window = projection_shock_window(years, first)
        except ValueError:
            window = (first, first)
        rule: ThresholdRule = (
            input6.threshold_rule if input6 is not None else "baseline_projection"
        )
        interactions = (
            bool(input6.interactions_on)
            if input6 is not None
            else bool(fx_passthrough)
        )
        path = ShockedMacroPath(
            baseline=baseline_macro,
            shocked=macro,
            metadata=ShockMetadata(
                shock_window_years=window,
                fx_depreciation_pct=float(fx_depreciation_pct),
                threshold_rule=rule,
                interactions_on=interactions,
                exports_shocked_in_levels=bool(combo_primary),
                primary_exp_gdp_denominator=primary_exp_gdp_denominator,
                lcu_deflator_growth=lcu_deflator_growth,
            ),
        )
        historical = scenario_id.startswith("A1_Historical")
        gfn = PublicGFNIdentity.from_path(
            path,
            input6=input6,
            inflation_elasticity=inflation_elasticity,
            fx_passthrough=fx_passthrough,
            market_access=market_access,
            gdp_lcu=gdp_lcu_override,
            historical=historical,
            external=external,
            external_dsa_borrowing_usd=external_dsa_borrowing_usd,
        )
        return cls(
            path=path,
            external=external,
            resfin=resfin,
            inflation_elasticity=float(inflation_elasticity),
            fx_passthrough=float(fx_passthrough),
            market_access=bool(market_access),
            resfin_external_ds=resfin_external_ds,
            gfn=gfn,
            scenario_id=scenario_id,
            _combo_primary_override=bool(combo_primary),
            _gdp_lcu_cache=(
                gdp_lcu_override.astype(float) if gdp_lcu_override is not None else None
            ),
        )

    # --- Field adapters matching legacy StressPublicBook attribute names ---

    @property
    def macro(self) -> MacroDebtBook:
        return self.path.shocked

    @property
    def baseline_macro(self) -> MacroDebtBook:
        return self.path.baseline

    @property
    def fx_depreciation_pct(self) -> float:
        return float(self.path.metadata.fx_depreciation_pct)

    @property
    def combo_primary(self) -> bool:
        if self._combo_primary_override is not None:
            return bool(self._combo_primary_override)
        return bool(
            self.path.metadata.exports_shocked_in_levels
            and self.path.metadata.fx_depreciation_pct
        )

    @property
    def input6(self) -> Input6StandardParams | None:
        return self.gfn.input6 if self.gfn is not None else None

    @property
    def gdp_lcu_override(self) -> pd.Series | None:
        if self.gfn is not None and self.gfn._gdp_lcu_cache is not None:
            return self.gfn._gdp_lcu_cache
        return None

    @property
    def external_dsa_borrowing_usd(self) -> pd.Series | None:
        return (
            self.gfn.external_dsa_borrowing_usd if self.gfn is not None else None
        )

    @property
    def primary_exp_gdp_denominator(self) -> pd.Series | None:
        return self.path.metadata.primary_exp_gdp_denominator

    @property
    def lcu_deflator_growth(self) -> pd.Series | None:
        return self.path.metadata.lcu_deflator_growth

    def _book(self):
        """Legacy adapter: thin ``StressPublicBook`` wrapping these ratios."""
        from lic_dsf.stress.public import StressPublicBook

        return StressPublicBook.from_ratios(self)


    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon."""
        return self.path.years

    def _is_historical(self) -> bool:
        return self.scenario_id.startswith("A1_Historical")

    def _uses_custom_debt_dynamics(self) -> bool:
        """Excel ``Customized Scenario - public`` R121 uses prior + R15 at t0.

        Standard B-sheets pin the first projection year to Macro face stock.
        A2 R123 = (R188 + R178) / R151 with R121_t = R121_{t-1} + R125_t.
        """
        return self.scenario_id.startswith("A2_Custom")

    def gdp_lcu(self) -> pd.Series:
        """Public B-sheet R41 shocked GDP in LCU."""
        if self.gfn is not None:
            return self.gfn.gdp_lcu()
        if self._gdp_lcu_cache is None:
            if self.gdp_lcu_override is not None:
                self._gdp_lcu_cache = self.gdp_lcu_override.astype(float)
            elif self._is_historical():
                self._gdp_lcu_cache = _a1_public_gdp_lcu(self.baseline_macro)
            else:
                self._gdp_lcu_cache = _b1_public_gdp_lcu(
                    self.baseline_macro,
                    self.macro,
                    self.inflation_elasticity,
                    fx_passthrough=self.fx_passthrough,
                    fx_depreciation_pct=self.fx_depreciation_pct,
                )
        return self._gdp_lcu_cache

    def _resfin_external_lcu(self) -> pd.Series:
        fx = self.macro.fx_pa()
        return _align(self.resfin.ext.pv, self.years).fillna(0.0) * _align(
            fx, self.years
        ).fillna(1.0)

    def _resfin_domestic_debt(self) -> pd.Series:
        return _align(self.resfin.dom_mlt.stock, self.years).fillna(0.0) + _align(
            self.resfin.dom_st.stock, self.years
        ).fillna(0.0)

    def _market_add_int_interest_usd(self) -> pd.Series:
        """``PV_ResFin-add.int.cost - mkt`` R34 additional external interest."""
        if not self.market_access:
            return pd.Series(0.0, index=list(self.years), dtype=float)
        stock = self._market_add_int_stock_usd()
        ext_rate, _dom = _market_add_int_rates(self.baseline_macro, self.macro)
        prior = stock.shift(1).fillna(0.0)
        return (prior * ext_rate).astype(float)

    def _market_add_int_stock_usd(self) -> pd.Series:
        """Add.int face stock: shock-window forex disb only, then amortize."""
        years = list(self.years)
        first = self.macro.inputs.first_projection_year
        proj = [y for y in years if y >= first]
        shock_years = _shock_window_years(self.years, first)
        disb = _align(self.resfin.fill.external_mlt_usd, self.years).fillna(0.0)
        new_borrowing = [
            float(disb.loc[y]) if y in shock_years else 0.0 for y in proj
        ]
        stock_proj = _amortizing_stock_from_disbursements(
            new_borrowing, grace=4, maturity=9
        )
        out = pd.Series(0.0, index=years, dtype=float)
        for year, value in zip(proj, stock_proj, strict=True):
            out.loc[year] = float(value)
        return out.astype(float)

    def _market_add_int_pv_usd(self) -> pd.Series:
        """``PV_ResFin-add.int.cost - mkt`` R32 PV of future add. interest.

        Excel's B2 market sheet adds this overlay from the second shock year
        onward (``G91``+), not in the first shock year (``F91``).
        """
        if not self.market_access:
            return pd.Series(0.0, index=list(self.years), dtype=float)
        interest = self._market_add_int_interest_usd()
        years = list(self.years)
        first = self.macro.inputs.first_projection_year
        proj = [y for y in years if y >= first]
        first_add_year = proj[2] if len(proj) >= 3 else (proj[-1] if proj else None)
        discount = 0.05
        ext_rate, _dom = _market_add_int_rates(self.baseline_macro, self.macro)
        out = pd.Series(0.0, index=years, dtype=float)
        for i, year in enumerate(years):
            if first_add_year is None or year < first_add_year:
                continue
            future = interest.iloc[i + 1 :].astype(float).tolist()
            if not future:
                continue
            if ext_rate > discount:
                out.loc[year] = float(sum(future))
            else:
                out.loc[year] = float(
                    sum(v / ((1.0 + discount) ** (k + 1)) for k, v in enumerate(future))
                )
        return out.astype(float)

    def _resfin_ext_stock_usd(self) -> pd.Series:
        """Face stock of public ResFin external MLT (USD)."""
        external = self.resfin.ext.instrument.external()
        key = "Stock of new forex debt (in USD)"
        years = list(self.years)
        if key not in external.index:
            return _align(self.resfin.ext.pv, self.years).fillna(0.0)
        values = {
            year: float(external.loc[key, year]) if year in external.columns else 0.0
            for year in years
        }
        return pd.Series(values, dtype=float)

    def _external_pv_usd(self) -> pd.Series:
        """Baseline Ext PPG PV + public ResFin PV (+ market add.int PV)."""
        return (
            _align(self.external.total_pv_of_debt(), self.years).fillna(0.0)
            + _align(self.resfin.ext.pv, self.years).fillna(0.0)
            + self._market_add_int_pv_usd()
        ).astype(float)

    def _external_ppg_debt_service_usd(self) -> pd.Series:
        """PPG external DS + ResFin service (+ market add.int interest).

        Market-access Excel wires DS to the non-mkt ResFin block (R145) plus
        add.int interest, while PV uses the market ResFin block (R111).
        """
        ds_resfin = self.resfin_external_ds or self.resfin
        return (
            _align(self.baseline_macro.ppg_interest(), self.years).fillna(0.0)
            + _align(self.baseline_macro.ppg_amortization(), self.years).fillna(0.0)
            + _align(ds_resfin.ext.interest, self.years).fillna(0.0)
            + _align(ds_resfin.ext.amortization, self.years).fillna(0.0)
            + self._market_add_int_interest_usd()
        ).astype(float)

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet external PV / GDP (R101)."""
        gdp_usd = self.gdp_lcu() / _align(self.macro.fx_pa(), self.years).replace(
            0.0, pd.NA
        )
        return _clamp_nonnegative(_pct(self._external_pv_usd(), gdp_usd))

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet external PV / exports (R102)."""
        return _clamp_nonnegative(
            _pct(self._external_pv_usd(), self.baseline_macro.exports())
        )

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet PPG DS / exports (R103)."""
        return _clamp_nonnegative(
            _pct(
                self._external_ppg_debt_service_usd(),
                self.baseline_macro.exports(),
            )
        )

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet PPG DS / revenue excl. grants (R104)."""
        return _clamp_nonnegative(
            _pct(
                self._external_ppg_debt_service_usd(),
                self.baseline_macro.revenues_excl_grants(),
            )
        )

    def _external_face_lcu(self) -> pd.Series:
        """B-sheet R82: Macro external LCU + ResFin face × FX(eop)."""
        if self._external_face_cache is None:
            self._external_face_cache = _public_external_face_lcu_path(
                self.baseline_macro,
                self.macro,
                self.resfin,
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=self.fx_depreciation_pct,
                combo_primary=self.combo_primary,
                resfin_ext_stock_usd=self._resfin_ext_stock_usd(),
            )
        return self._external_face_cache

    def _external_pv_lcu(self) -> pd.Series:
        """B-sheet R91: Macro PV LCU + ResFin PV × FX(eop).

        B2 market-access Excel also adds ``PV_ResFin-add.int.cost - mkt`` R32
        (PV of future add.interest) × shocked ``fx_eop``. B6 folds add.int into
        the combo DS/ResFin path instead — do not double-count there.
        """
        if self._external_pv_cache is None:
            base = _public_external_pv_lcu_path(
                self.baseline_macro,
                self.macro,
                self.resfin,
                self._external_face_lcu(),
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=self.fx_depreciation_pct,
                combo_primary=self.combo_primary,
            )
            if self.market_access and not self.combo_primary:
                fx_eop = _align(self.macro.fx_eop(), self.years).fillna(1.0)
                base = (base + self._market_add_int_pv_usd() * fx_eop).astype(float)
            self._external_pv_cache = base
        return self._external_pv_cache

    def _resfin_in_debt_service_parts(self) -> bool:
        """True when R84–R87 parts already fold in ResFin (B5 / B6)."""
        return self.combo_primary or bool(
            self.fx_passthrough and self.fx_depreciation_pct
        )

    def _existing_debt_service_parts_lcu(
        self,
    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """Baseline existing debt service split for B-sheet R84–R87."""
        return _public_existing_debt_service_parts_lcu(
            self.baseline_macro,
            self.macro,
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
            combo_primary=self.combo_primary,
            input6=self.input6,
            external=self.external,
            inflation_elasticity=self.inflation_elasticity,
            resfin=self.resfin if self._resfin_in_debt_service_parts() else None,
            market_access=self.market_access,
            external_dsa_borrowing_usd=self.external_dsa_borrowing_usd,
            gdp_lcu=self.gdp_lcu() if self.combo_primary else None,
        )

    def _resfin_dom_interest_lcu(self) -> pd.Series:
        """ResFin domestic interest (B1; included in B5/B6 parts)."""
        dom_mlt = _align(self.resfin.dom_mlt.interest, self.years).fillna(0.0)
        dom_st = _align(self.resfin.dom_st.interest, self.years).fillna(0.0)
        return (dom_mlt + dom_st).astype(float)

    def _resfin_ext_interest_lcu(self) -> pd.Series:
        """ResFin external interest in LCU (B1; included in B5/B6 parts)."""
        fx = _align(self.baseline_macro.fx_pa(), self.years)
        return (_align(self.resfin.ext.interest, self.years).fillna(0.0) * fx).astype(
            float
        )

    def _interest_domestic_lcu(self) -> pd.Series:
        """B-sheet R86: domestic interest + ResFin domestic interest.

        B2 market-access also adds domestic add.int legs (``mkt`` R113/R122).
        B6 already includes those in ``_combo_public_debt_service_parts_lcu``.
        """
        dom_i, _, _, _ = self._existing_debt_service_parts_lcu()
        if self._resfin_in_debt_service_parts():
            return dom_i.astype(float)
        out = (dom_i + self._resfin_dom_interest_lcu()).astype(float)
        if self.market_access and not self.combo_primary:
            _ext, mkt_mlt, mkt_st = _market_add_int_interest_parts(
                self.resfin, self.macro, self.baseline_macro
            )
            out = (out + mkt_mlt + mkt_st).astype(float)
        return out

    def _interest_external_lcu(self) -> pd.Series:
        """B-sheet R87: PPG external interest + ResFin external interest.

        B2 market-access also adds external add.int interest × shocked
        ``fx_pa`` (``mkt`` R100). B6 already folds this into combo parts.
        """
        _, ppg_i, _, _ = self._existing_debt_service_parts_lcu()
        if self._resfin_in_debt_service_parts():
            return ppg_i.astype(float)
        out = (ppg_i + self._resfin_ext_interest_lcu()).astype(float)
        if self.market_access and not self.combo_primary:
            mkt_ext_usd, _mlt, _st = _market_add_int_interest_parts(
                self.resfin, self.macro, self.baseline_macro
            )
            fx = _align(self.macro.fx_pa(), self.years).fillna(1.0)
            out = (out + mkt_ext_usd * fx).astype(float)
        return out

    def _interest_total_lcu(self) -> pd.Series:
        """B-sheet R85."""
        return (self._interest_domestic_lcu() + self._interest_external_lcu()).astype(
            float
        )

    def _amortization_excl_st_lcu(self) -> pd.Series:
        """B-sheet R84: amortisation excl. ST domestic + ResFin amort."""
        _, _, third, fourth = self._existing_debt_service_parts_lcu()
        if self._resfin_in_debt_service_parts():
            # B5/B6 parts: (…, ext_amort_bundle, dom_resfin_amort).
            return (third + fourth).astype(float)
        # B1 parts: (…, dom_amort, ext_amort); add ResFin separately.
        return (
            third
            + fourth
            + _align(self.resfin.ext.amortization, self.years).fillna(0.0)
            * _align(self.baseline_macro.fx_pa(), self.years)
            + _align(self.resfin.dom_mlt.amortization, self.years).fillna(0.0)
        ).astype(float)

    def _st_domestic_stock_lcu(self) -> pd.Series:
        """B-sheet R81: Macro ST + ResFin ST."""
        if self._domestic_st_cache is None:
            self._domestic_st_cache = _public_domestic_st_lcu_path(
                self.macro,
                self.resfin,
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=self.fx_depreciation_pct,
                combo_primary=self.combo_primary,
            )
        return self._domestic_st_cache

    def _domestic_face_lcu(self) -> pd.Series:
        """B-sheet R80 domestic face from debt dynamics (R79 − R82)."""
        if self._domestic_face_cache is None:
            self.public_sector_debt_to_gdp()
        assert self._domestic_face_cache is not None
        return self._domestic_face_cache

    def _revenue_to_gdp(self) -> pd.Series:
        """B-sheet R18 revenue+grants / GDP under stress.

        First projection year uses the baseline ratio. Later years hold
        baseline (revenue − grants)/GDP and add shocked grants / shocked GDP
        (Excel ``Baseline R24 − R25 + grants/R41``).
        """
        years = self.years
        first = self.macro.inputs.first_projection_year
        base_rev = _pct(
            self.baseline_macro.revenues_incl_grants(),
            self.baseline_macro.gdp_lcu(),
        )
        base_grants = _pct(self.baseline_macro.grants(), self.baseline_macro.gdp_lcu())
        shock_gdp = self.gdp_lcu()
        # Excel R19 = Macro grants (baseline levels) / shocked R41.
        grants_to_gdp = _pct(
            _align(self.baseline_macro.grants(), years), shock_gdp
        )

        out = pd.Series(0.0, index=list(years), dtype=float)
        drop_ppt = None
        if self.primary_exp_gdp_denominator is not None:
            # Excel C3 R18: subtract AA66 revenue-drop ppt (faded) after year 1.
            gdp_b = _align(self.baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
            gdp_m = _align(self.macro.gdp_lcu(), years).replace(0.0, pd.NA)
            grants_lcu = _align(self.baseline_macro.grants(), years).fillna(0.0)
            rev_excl_b = (
                _align(self.baseline_macro.revenues_incl_grants(), years).fillna(0.0)
                - grants_lcu
            )
            held = rev_excl_b * (gdp_m / gdp_b) + grants_lcu
            drop_lcu = held - _align(
                self.macro.revenues_incl_grants(), years
            ).fillna(0.0)
            drop_ppt = (drop_lcu / gdp_m * 100.0).astype(float)
        for year in years:
            if year < first:
                out.loc[year] = float(base_rev.reindex([year]).fillna(0.0).loc[year])
            elif year == first:
                out.loc[year] = float(base_rev.loc[year])
            else:
                out.loc[year] = (
                    float(base_rev.loc[year])
                    - float(base_grants.loc[year])
                    + float(grants_to_gdp.loc[year])
                )
                if drop_ppt is not None:
                    out.loc[year] = float(out.loc[year]) - float(
                        drop_ppt.reindex([year]).fillna(0.0).loc[year]
                    )
        return out.astype(float)

    def _residual_flow_to_gdp(self) -> pd.Series:
        """B-sheet R32: baseline residual × baseline GDP / shocked GDP."""
        from lic_dsf.dsa.baseline.public import BaselinePublicBook

        base_book = BaselinePublicBook(
            macro=self.baseline_macro, external=self.external
        )
        residual = base_book.residual_public_flows()
        base_gdp = _align(self.baseline_macro.gdp_lcu(), self.years)
        shock_gdp = self.gdp_lcu()
        return (
            _align(residual, self.years) * base_gdp / shock_gdp.replace(0.0, pd.NA)
        ).astype(float)

    def _debt_dynamics_debt_to_gdp(self) -> pd.Series:
        """B-sheet R11: public debt / GDP via Excel debt-dynamics identity.

        ``R11_t = R11_{t-1} + R15_t`` with automatic dynamics (R23–R25), primary
        deficit, other identified flows, and baseline residual (R32). Domestic
        face stock is the residual ``R79 − R82`` (not baseline + ResFin add).
        """
        years = list(self.years)
        first = self.macro.inputs.first_projection_year
        gdp = self.gdp_lcu()
        fx_eop = _align(self.macro.fx_eop(), self.years)
        fx_eop_baseline = _align(self.baseline_macro.fx_eop(), self.years)
        fx_pa = _align(self.macro.fx_pa(), self.years)

        real_s, defl_s = _public_real_and_lcu_deflator(
            self.baseline_macro,
            self.macro,
            self.inflation_elasticity,
            historical=self._is_historical(),
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
        )
        if self.lcu_deflator_growth is not None:
            # C3_commodity_prices_pub R54 AA69 path overrides baseline deflator.
            shock_const = _align(self.macro.gdp_constant(), self.years).replace(
                0.0, pd.NA
            )
            real_s = _growth_pct(shock_const)
            defl_s = _align(self.lcu_deflator_growth, self.years).astype(float)
        us_defl = _align(self.macro.foreign_deflator_growth(), self.years)

        r82 = self._external_face_lcu()
        r86 = self._interest_domestic_lcu()
        r87 = self._interest_external_lcu()
        if self._is_historical():
            prim = _a1_primary_deficit_lcu(self.baseline_macro, gdp)
        elif self.combo_primary:
            assert self.input6 is not None
            prim = _combo_primary_deficit_lcu(
                self.baseline_macro,
                gdp,
                self.input6,
                self.external,
                inflation_elasticity=self.inflation_elasticity,
            )
        else:
            prim = _b1_primary_deficit_lcu(
                self.baseline_macro,
                self.macro,
                gdp,
                primary_exp_gdp_denominator=self.primary_exp_gdp_denominator,
                use_shocked_revenues=self.primary_exp_gdp_denominator is not None,
            )
        other = _b1_other_identified_flows_lcu(self.macro)
        residual = self._residual_flow_to_gdp()

        r11 = pd.Series(0.0, index=years, dtype=float)
        r12 = pd.Series(0.0, index=years, dtype=float)
        r79 = pd.Series(0.0, index=years, dtype=float)
        r80 = pd.Series(0.0, index=years, dtype=float)

        for year in years:
            if year < first:
                # Pre-projection: use Macro face debt / baseline-style GDP.
                g_y = float(gdp.loc[year]) if year in gdp.index else 0.0
                if g_y != 0.0:
                    r11.loc[year] = (
                        float(self.macro.total_public_debt().loc[year]) / g_y * 100.0
                    )
                    r79.loc[year] = float(r11.loc[year]) / 100.0 * g_y
                    r80.loc[year] = float(r79.loc[year]) - float(r82.loc[year])
                    r12.loc[year] = float(r82.loc[year]) / g_y * 100.0
                continue
            g_y = float(gdp.loc[year])
            if g_y == 0.0:
                continue
            if year == first and not self._uses_custom_debt_dynamics():
                r11.loc[year] = (
                    float(self.macro.total_public_debt().loc[year]) / g_y * 100.0
                )
            else:
                prev = year - 1
                g = float(real_s.loc[year]) if pd.notna(real_s.loc[year]) else 0.0
                pi = float(defl_s.loc[year]) if pd.notna(defl_s.loc[year]) else 0.0
                pi_us = (
                    float(us_defl.loc[year]) if pd.notna(us_defl.loc[year]) else 0.0
                )
                den = 1.0 + g / 100.0
                fx_dep_year = _fx_shock_projection_year(tuple(years), first)
                fx_pa_baseline = _align(self.baseline_macro.fx_pa(), self.years)
                b5 = bool(self.fx_passthrough and self.fx_depreciation_pct)
                fx_shock_year = (
                    b5
                    and fx_dep_year is not None
                    and year == fx_dep_year
                )
                # B5 R44: Macro eop_{t-1} / Macro pa_t (baseline FX on Macro sheet).
                if b5:
                    fx_i_ext = float(fx_eop_baseline.loc[prev]) / float(
                        fx_pa_baseline.loc[year]
                    )
                elif fx_shock_year:
                    fx_i_ext = float(fx_eop.loc[prev]) / float(
                        fx_pa_baseline.loc[year]
                    )
                else:
                    fx_i_ext = float(fx_eop.loc[prev]) / float(fx_pa.loc[year])
                i_ext = (
                    float(r87.loc[year])
                    / float(r82.loc[prev])
                    * 100.0
                    * fx_i_ext
                )
                # R25 uses R48 from the same R44 FX conversion as R46.
                fx_i_ext_r25 = (
                    fx_i_ext
                    if b5
                    else float(fx_eop.loc[prev]) / float(fx_pa.loc[year])
                )
                i_ext_r25 = (
                    float(r87.loc[year])
                    / float(r82.loc[prev])
                    * 100.0
                    * fx_i_ext_r25
                )
                i_dom = (
                    float(r86.loc[year]) / float(r80.loc[prev]) * 100.0
                    if float(r80.loc[prev]) != 0.0
                    else 0.0
                )
                r_dom = (i_dom - pi) / (1.0 + pi / 100.0)
                r_ext = (i_ext - pi_us) / (1.0 + pi_us / 100.0)
                r_ext_r25 = (i_ext_r25 - pi_us) / (1.0 + pi_us / 100.0)
                share = float(r12.loc[prev]) / float(r11.loc[prev])
                r_avg = share * r_ext + (1.0 - share) * r_dom
                # B5 R50/R53: nominal dep from full-depreciation R49 eop path.
                if self.combo_primary and fx_shock_year:
                    fx_for_nom_dep = fx_eop_baseline
                elif b5:
                    fx_for_nom_dep = _b5_public_fx_eop_for_debt_service(
                        self.baseline_macro,
                        fx_depreciation_pct=self.fx_depreciation_pct,
                    )
                elif fx_shock_year:
                    fx_for_nom_dep = fx_pa
                else:
                    fx_for_nom_dep = fx_eop
                nom_dep = (
                    float(fx_for_nom_dep.loc[year])
                    / float(fx_for_nom_dep.loc[prev])
                    - 1.0
                ) * 100.0
                real_dep = (
                    (100.0 + nom_dep)
                    * (1.0 + pi_us / 100.0)
                    / (1.0 + pi / 100.0)
                    - 100.0
                )
                r23 = (r_avg / 100.0) * float(r11.loc[prev]) / den
                r24 = -(g / 100.0) * float(r11.loc[prev]) / den
                r25 = (
                    (real_dep / 100.0)
                    * float(r12.loc[prev])
                    * (1.0 + r_ext_r25 / 100.0)
                    / den
                )
                r15 = (
                    float(prim.loc[year]) / g_y * 100.0
                    + r23
                    + r24
                    + r25
                    + float(other.loc[year]) / g_y * 100.0
                    + float(residual.loc[year])
                )
                r11.loc[year] = float(r11.loc[prev]) + r15

            r79.loc[year] = float(r11.loc[year]) / 100.0 * g_y
            r80.loc[year] = float(r79.loc[year]) - float(r82.loc[year])
            r12.loc[year] = float(r82.loc[year]) / g_y * 100.0

        self._domestic_face_cache = r80.astype(float)
        return r11.astype(float)

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Public debt / GDP (B-sheet R11 debt-dynamics path)."""
        if self._debt_to_gdp_cache is None:
            self._debt_to_gdp_cache = self._debt_dynamics_debt_to_gdp()
        return self._debt_to_gdp_cache

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """PV of public debt / GDP (B-sheet R13).

        Excel: ``(R91 + R80) / R41 × 100`` where domestic face ``R80`` is the
        residual from the R11 dynamics path, not baseline domestic + ResFin.
        """
        gdp = self.gdp_lcu()
        r91 = self._external_pv_lcu()
        r80 = self._domestic_face_lcu()
        return _clamp_nonnegative(_pct(r91 + r80, gdp))

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """PV of public debt / revenue+grants (B-sheet R95 = R13 / R18 × 100)."""
        return (
            self.pv_public_debt_to_gdp()
            / self._revenue_to_gdp().replace(0.0, pd.NA)
            * 100.0
        ).astype(float)

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Debt service / revenue+grants (B-sheet R93).

        Excel: ``10000 × (R84 + R85 + prior R81) / (R18 × R41)``.
        """
        gdp = self.gdp_lcu()
        rev = self._revenue_to_gdp()
        st = self._st_domestic_stock_lcu()
        numer = (
            self._amortization_excl_st_lcu()
            + self._interest_total_lcu()
            + st.shift(1).fillna(0.0)
        )
        return _clamp_nonnegative(
            10000.0 * numer / (rev.replace(0.0, pd.NA) * gdp.replace(0.0, pd.NA))
        ).astype(float)

    def public_gfn(self) -> pd.Series:
        """B1 R90 public GFN (LCU)."""
        if self.gfn is not None:
            return self.gfn.compute_gfn(self.resfin)
        return estimate_b1_public_gfn(
            self.baseline_macro,
            self.macro,
            self.resfin,
            inflation_elasticity=self.inflation_elasticity,
            gdp_lcu=self.gdp_lcu(),
            market_access=self.market_access,
            historical=self._is_historical(),
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
            combo_primary=self.combo_primary,
            input6=self.input6,
            external=self.external,
            prior_st=self._st_domestic_stock_lcu(),
        )

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP (B-sheet R94 = 100 × DS / R41)."""
        gdp = self.gdp_lcu()
        st = self._st_domestic_stock_lcu()
        numer = (
            self._amortization_excl_st_lcu()
            + self._interest_total_lcu()
            + st.shift(1).fillna(0.0)
        )
        return _clamp_nonnegative(_pct(numer, gdp))

__all__ = ["StressPublicRatios"]

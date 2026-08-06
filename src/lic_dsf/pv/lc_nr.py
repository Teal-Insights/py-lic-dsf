"""Local-currency non-resident bond PV (PV_LC_NR1/2/3-shaped)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.mathutil import excel_npv


def _as_float_list(values: Sequence[float], horizon: int) -> list[float]:
    out = [float(v) for v in values]
    if len(out) < horizon:
        out.extend([0.0] * (horizon - len(out)))
    return out[:horizon]


@dataclass(slots=True)
class LocalCurrencyNonResidentInstrument:
    """One LC-denominated locally-issued bond held by non-residents.

    Mirrors ``PV_LC_NR*``: per-disbursement-year cohorts in LC, converted to USD
    with period-average FX for flows and end-of-period FX for stocks.

    Args:
        name: Instrument label (e.g. ``Bonds (1 to 3 years)-LC``).
        grace: Grace period in years.
        maturity: Maturity in years (must be ``> grace``).
        discount_rate: DSA discount rate.
        interest_rates: LC contractual rate by projection year.
        disbursements_lc: New borrowing in LC by projection year.
        fx_pa: FX period-average (LC per USD) by year.
        fx_eop: FX end-of-period (LC per USD) by year.
        years: Optional calendar year labels.
        horizon: Projection length; defaults to ``len(disbursements_lc)``.
    """

    name: str
    grace: int
    maturity: int
    discount_rate: float
    interest_rates: Sequence[float]
    disbursements_lc: Sequence[float]
    fx_pa: Sequence[float]
    fx_eop: Sequence[float]
    years: Sequence[int] | None = None
    horizon: int | None = None

    def __post_init__(self) -> None:
        if self.grace < 0:
            raise ValueError(f"grace must be >= 0, got {self.grace}")
        if self.maturity <= self.grace:
            raise ValueError(
                f"maturity must be > grace, got maturity={self.maturity}, "
                f"grace={self.grace}"
            )
        if self.horizon is not None and self.horizon < 1:
            raise ValueError(f"horizon must be >= 1, got {self.horizon}")
        n = len(self.disbursements_lc)
        for label, series in (
            ("interest_rates", self.interest_rates),
            ("fx_pa", self.fx_pa),
            ("fx_eop", self.fx_eop),
        ):
            if len(series) != n and self.horizon is None:
                # Allow shorter series only when horizon is explicit; else require
                # matching lengths for the natural disbursement horizon.
                if len(series) < n:
                    raise ValueError(
                        f"{label} length {len(series)} < disbursements "
                        f"length {n}"
                    )
        if self.years is not None and len(self.years) != n:
            raise ValueError(
                "years must be the same length as disbursements_lc "
                f"({len(self.years)} != {n})"
            )

    def _horizon(self) -> int:
        if self.horizon is not None:
            return self.horizon
        return max(len(self.disbursements_lc), self.maturity + 1)

    def _years(self) -> list[object]:
        horizon = self._horizon()
        if self.years is None:
            return list(range(horizon))
        values = list(self.years)
        if len(values) < horizon:
            step = 1
            if len(values) >= 2:
                step = values[-1] - values[-2]
            while len(values) < horizon:
                values.append(values[-1] + step)
        return values[:horizon]

    def _padded_inputs(
        self,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        horizon = self._horizon()
        return (
            _as_float_list(self.disbursements_lc, horizon),
            _as_float_list(self.interest_rates, horizon),
            _as_float_list(self.fx_pa, horizon),
            _as_float_list(self.fx_eop, horizon),
        )

    def _cohort_series(
        self,
        vintage: int,
        disbursements_lc: list[float],
        interest_rates: list[float],
        fx_pa: list[float],
        fx_eop: list[float],
    ) -> tuple[list[float], list[float], list[float], list[float], list[float]]:
        """Return USD stock, PV, TDS, interest, amort for one vintage."""
        horizon = len(disbursements_lc)
        span = float(self.maturity - self.grace)
        rate_v = interest_rates[vintage]

        # Cohort LC disbursement only in the vintage year.
        disb = [0.0] * horizon
        disb[vintage] = disbursements_lc[vintage]

        cumulative = [0.0] * horizon
        running = 0.0
        for t in range(horizon):
            running += disb[t]
            cumulative[t] = running

        def cum_at_offset(offset: int) -> float:
            if offset <= 0:
                return 0.0
            idx = offset - 1
            if idx >= horizon:
                return cumulative[-1]
            return cumulative[idx]

        amort_lc = [0.0] * horizon
        for t in range(horizon):
            # PV_LC_NR uses projection column index (0..n), not years-since-vintage.
            tg = max(t - self.grace, 0)
            tm = max(t - self.maturity, 0)
            if tg == 0:
                amort_lc[t] = 0.0
            else:
                amort_lc[t] = (cum_at_offset(tg) - cum_at_offset(tm)) / span

        stock_lc = [0.0] * horizon
        for t in range(horizon):
            if t == vintage:
                stock_lc[t] = disb[t]
            elif t < vintage:
                stock_lc[t] = 0.0
            else:
                stock_lc[t] = stock_lc[t - 1] - amort_lc[t]
                if abs(stock_lc[t]) < 1e-12:
                    stock_lc[t] = 0.0

        stock_usd = [0.0] * horizon
        interest_usd = [0.0] * horizon
        amort_usd = [0.0] * horizon
        for t in range(horizon):
            if stock_lc[t] == 0.0 or fx_eop[t] == 0.0:
                stock_usd[t] = 0.0
            else:
                stock_usd[t] = stock_lc[t] / fx_eop[t]
            if amort_lc[t] == 0.0 or fx_pa[t] == 0.0:
                amort_usd[t] = 0.0
            else:
                amort_usd[t] = amort_lc[t] / fx_pa[t]
            if t == 0 or t < vintage or fx_pa[t] == 0.0:
                interest_usd[t] = 0.0
            else:
                # Excel: rate(vintage) * prior LC stock / current FX(pa)
                interest_usd[t] = rate_v * stock_lc[t - 1] / fx_pa[t]

        tds = [interest_usd[t] + amort_usd[t] for t in range(horizon)]

        pv_usd = [0.0] * horizon
        for t in range(horizon):
            if vintage > t:
                pv_usd[t] = 0.0
                continue
            future = tds[t + 1 :]
            npv = excel_npv(self.discount_rate, future) if future else 0.0
            # Cap at USD stock (LIC-DSF IF(NPV > stock, stock, NPV)).
            pv_usd[t] = min(npv, stock_usd[t]) if stock_usd[t] else 0.0

        return stock_usd, pv_usd, tds, interest_usd, amort_usd

    def _aggregate_cohorts(
        self,
    ) -> tuple[
        list[float],
        list[float],
        list[float],
        list[float],
        list[float],
        list[float],
        list[float],
    ]:
        disb, rates, fx_pa, fx_eop = self._padded_inputs()
        horizon = self._horizon()
        stock = [0.0] * horizon
        pv = [0.0] * horizon
        tds = [0.0] * horizon
        interest = [0.0] * horizon
        amort = [0.0] * horizon
        for vintage, amount in enumerate(disb):
            if amount == 0.0:
                continue
            c_stock, c_pv, c_tds, c_int, c_amort = self._cohort_series(
                vintage, disb, rates, fx_pa, fx_eop
            )
            for t in range(horizon):
                stock[t] += c_stock[t]
                pv[t] += c_pv[t]
                tds[t] += c_tds[t]
                interest[t] += c_int[t]
                amort[t] += c_amort[t]
        cumulative = []
        running = 0.0
        for amount in disb:
            running += amount
            cumulative.append(running)
        return disb, cumulative, stock, pv, tds, interest, amort

    def external(self) -> pd.DataFrame:
        """Return Ext_Debt-facing USD summary panel (portfolio-compatible rows)."""
        columns = self._years()
        (
            disb_lc,
            cumulative_lc,
            stock_usd,
            pv_usd,
            tds,
            interest,
            amort,
        ) = self._aggregate_cohorts()
        _, _, fx_pa, _ = self._padded_inputs()
        disb_usd = [
            (disb_lc[t] / fx_pa[t]) if fx_pa[t] else 0.0 for t in range(len(disb_lc))
        ]
        cumulative_usd: list[float] = []
        running = 0.0
        for amount in disb_usd:
            running += amount
            cumulative_usd.append(running)
        return pd.DataFrame(
            [
                disb_lc,
                disb_usd,
                cumulative_usd,
                stock_usd,
                pv_usd,
                tds,
                interest,
                amort,
            ],
            index=[
                "New borrowing (gross, in local currency)",
                "New forex borrowing (gross, USD)",
                "cumulative",
                "Stock of new forex debt (in USD)",
                "PV of debt",
                "Total debt service (in USD)",
                "Interest",
                "Amortization",
            ],
            columns=columns,
        )

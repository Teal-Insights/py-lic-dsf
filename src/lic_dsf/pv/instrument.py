"""LIC-DSF-style present-value calculations for a single financing instrument.

Mirrors the standard ``PV_Base`` instrument template:

* ``internal()`` — unit loan of ``unit_base`` (default 100) as a DataFrame
  (debt stock, amortization, interest, PV, grant element, ``t-g`` / ``t-m``).
* ``external()`` — Output block scaled by disbursements as a DataFrame
  (new borrowing, cumulative, stock, PV, debt service, interest, amortization).

Year indexing matches LIC-DSF: column ``t`` uses age ``t - 1`` for the
grace/maturity amortization window on the unit loan.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.mathutil import age as _age
from lic_dsf.pv.mathutil import excel_npv as _excel_npv


@dataclass(slots=True)
class PresentValueInstrument:
    """One LIC-DSF external financing instrument.

    Args:
        name: Instrument / creditor label (e.g. ``IMF``, ``Eurobond``).
        grace: Grace period in years (integer).
        maturity: Loan maturity in years (integer, must be ``> grace``).
        interest_rate: Contractual interest rate (e.g. ``0.0075``).
        discount_rate: DSA discount rate (e.g. ``0.05`` from Input 1).
        disbursements: New borrowing by projection year (USD).
        unit_base: Notional principal for the internal schedule (LIC-DSF uses
            ``100``).
        years: Optional calendar year labels aligned with ``disbursements``.
        horizon: Number of projection steps to compute. Defaults to
            ``max(len(disbursements), maturity + 1)``.
    """

    name: str
    grace: int
    maturity: int
    interest_rate: float
    discount_rate: float
    disbursements: Sequence[float]
    unit_base: float = 100.0
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
        if self.unit_base <= 0:
            raise ValueError(f"unit_base must be > 0, got {self.unit_base}")
        if self.horizon is not None and self.horizon < 1:
            raise ValueError(f"horizon must be >= 1, got {self.horizon}")
        if self.years is not None and len(self.years) != len(self.disbursements):
            raise ValueError(
                "years must be the same length as disbursements "
                f"({len(self.years)} != {len(self.disbursements)})"
            )

    def _horizon(self) -> int:
        if self.horizon is not None:
            return self.horizon
        return max(len(self.disbursements), self.maturity + 1)

    def _solve_horizon(self) -> int:
        """Years needed so unit-loan NPV is not truncated mid-amortization."""
        return max(self._horizon(), self.maturity + 1)

    def _disbursements_padded(self) -> list[float]:
        horizon = self._horizon()
        values = [float(v) for v in self.disbursements]
        if len(values) < horizon:
            values.extend([0.0] * (horizon - len(values)))
        return values[:horizon]

    def _year_columns(self) -> list[object]:
        years = self._years_padded()
        if years is not None:
            return list(years)
        return list(range(self._horizon()))

    def _years_padded(self) -> tuple[int, ...] | None:
        if self.years is None:
            return None
        horizon = self._horizon()
        values = list(self.years)
        if len(values) < horizon:
            step = 1
            if len(values) >= 2:
                step = values[-1] - values[-2]
            while len(values) < horizon:
                values.append(values[-1] + step)
        return tuple(values[:horizon])

    def _unit_amortization(self, year_index: int) -> float:
        age = _age(year_index)
        if age < self.grace:
            return 0.0
        if age < self.maturity:
            return self.unit_base / (self.maturity - self.grace)
        return 0.0

    def _unit_loan_series(
        self, solve_horizon: int
    ) -> tuple[
        list[float],
        list[float],
        list[float],
        list[float],
        list[float],
        list[float],
    ]:
        amortization = [self._unit_amortization(t) for t in range(solve_horizon)]

        debt_stock: list[float] = []
        for t in range(solve_horizon):
            if t == 0:
                debt_stock.append(self.unit_base - amortization[0])
            else:
                debt_stock.append(debt_stock[t - 1] - amortization[t])

        interest: list[float] = []
        for t in range(solve_horizon):
            if t == 0:
                interest.append(0.0)
            else:
                interest.append(self.interest_rate * debt_stock[t - 1])

        total_debt_service = [
            amortization[t] + interest[t] for t in range(solve_horizon)
        ]

        pv_of_debt: list[float] = []
        for t in range(solve_horizon):
            if self.interest_rate >= self.discount_rate:
                pv_of_debt.append(debt_stock[t])
            else:
                future = total_debt_service[t + 1 :]
                pv_of_debt.append(_excel_npv(self.discount_rate, future))

        grant_element: list[float] = []
        for t in range(solve_horizon):
            stock = debt_stock[t]
            if stock == 0:
                grant_element.append(0.0)
            else:
                grant_element.append((1.0 - pv_of_debt[t] / stock) * 100.0)

        return (
            amortization,
            debt_stock,
            interest,
            total_debt_service,
            pv_of_debt,
            grant_element,
        )

    def internal(self) -> pd.DataFrame:
        """Return the internal (unit-loan) block as a PV_Base-shaped DataFrame.

        Index rows match the sheet labels. Columns are projection years (or
        ``0..horizon-1`` if ``years`` was not provided). A ``Term`` column holds
        scalar inputs (grace, maturity, rates); year cells hold the schedule.
        """
        horizon = self._horizon()
        solve_horizon = self._solve_horizon()
        year_index = list(range(horizon))
        columns = self._year_columns()
        (
            amortization,
            debt_stock,
            interest,
            total_debt_service,
            pv_of_debt,
            grant_element,
        ) = self._unit_loan_series(solve_horizon)

        t_minus_grace = [max(t - self.grace, 0) for t in year_index]
        t_minus_maturity = [max(t - self.maturity, 0) for t in year_index]
        empty = [pd.NA] * horizon
        base_row = [self.unit_base] + [pd.NA] * (horizon - 1)

        frame = pd.DataFrame(
            [
                [pd.NA, *year_index],
                [self.grace, *empty],
                [self.maturity, *base_row],
                [self.interest_rate, *debt_stock[:horizon]],
                [self.discount_rate, *amortization[:horizon]],
                [pd.NA, *interest[:horizon]],
                [pd.NA, *total_debt_service[:horizon]],
                [pd.NA, *pv_of_debt[:horizon]],
                [pd.NA, *grant_element[:horizon]],
                [pd.NA, *t_minus_grace],
                [pd.NA, *t_minus_maturity],
            ],
            index=[
                self.name,
                f"Grace {self.name}",
                f"Maturity {self.name} / Base",
                f"Interest {self.name} / Debt stock",
                f"Discount {self.name} / Amortization",
                "Interest",
                "Total debt service",
                "PV of debt",
                "Grant element",
                "t-g>0",
                "t-m condition",
            ],
            columns=["Term", *columns],
        )
        return frame

    def external(self) -> pd.DataFrame:
        """Return the Output block scaled by disbursements as a DataFrame.

        Columns are projection years. Rows are the Output metrics Ext_Debt_Data
        consumes. Years are column headers only (not repeated as a data row).
        """
        horizon = self._horizon()
        year_index = list(range(horizon))
        columns = self._year_columns()
        new_borrowing = self._disbursements_padded()

        cumulative: list[float] = []
        running = 0.0
        for amount in new_borrowing:
            running += amount
            cumulative.append(running)

        def choose_cumulative(offset: int) -> float:
            if offset <= 0:
                return 0.0
            idx = offset - 1
            if idx >= len(cumulative):
                return 0.0
            return cumulative[idx]

        amortization: list[float] = []
        span = float(self.maturity - self.grace)
        for t in year_index:
            tg = max(t - self.grace, 0)
            tm = max(t - self.maturity, 0)
            amortization.append((choose_cumulative(tg) - choose_cumulative(tm)) / span)

        stock: list[float] = []
        for t in year_index:
            if t == 0:
                stock.append(new_borrowing[0] - amortization[0])
            else:
                stock.append(stock[t - 1] + new_borrowing[t] - amortization[t])

        interest: list[float] = []
        for t in year_index:
            if t == 0:
                interest.append(0.0)
            else:
                interest.append(self.interest_rate * stock[t - 1])

        total_debt_service = [interest[t] + amortization[t] for t in year_index]

        year0 = self._year_columns()[0]
        unit_pv0 = float(self.internal().loc["PV of debt", year0])
        pv_of_debt: list[float] = []
        for t in year_index:
            if self.interest_rate >= self.discount_rate:
                if t == 0:
                    pv_of_debt.append(new_borrowing[0])
                else:
                    pv_of_debt.append(
                        pv_of_debt[t - 1] - amortization[t] + new_borrowing[t]
                    )
            else:
                unit_ratio = unit_pv0 / self.unit_base
                if t == 0:
                    pv_of_debt.append(new_borrowing[0] * unit_ratio)
                else:
                    pv_of_debt.append(
                        pv_of_debt[t - 1] * (1.0 + self.discount_rate)
                        - total_debt_service[t]
                        + new_borrowing[t] * unit_ratio
                    )

        return pd.DataFrame(
            [
                new_borrowing,
                cumulative,
                stock,
                pv_of_debt,
                total_debt_service,
                interest,
                amortization,
            ],
            index=[
                "New forex borrowing (gross, USD)",
                "cumulative",
                "Stock of new forex debt (in USD)",
                f"PV of debt   {self.name}",
                "Total debt service (in USD)",
                "Interest",
                "Amortization",
            ],
            columns=columns,
        )


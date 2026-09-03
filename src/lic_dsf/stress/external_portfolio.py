"""LC-NR FX portfolio revaluation for B5/B6 (Phase 7)."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.pv.portfolio import PVPortfolio
from lic_dsf.stress.path import ShockedMacroPath


@dataclass(frozen=True, slots=True)
class ExternalPortfolioAdjuster:
    """Rebuild Ext with shocked FX so LC-NR USD PV/stock revalue (B5/B6)."""

    def adjust(
        self,
        external: ExternalDebtBook,
        path: ShockedMacroPath,
    ) -> ExternalDebtBook:
        """Return a copy of ``external`` with LC-NR instruments on shocked FX."""
        return self.rebuild(external, path.shocked.fx_pa(), path.shocked.fx_eop())

    @staticmethod
    def rebuild(
        external: ExternalDebtBook,
        fx_pa: pd.Series,
        fx_eop: pd.Series,
    ) -> ExternalDebtBook:
        """Port of ``stress.scenario.rebuild_external_with_fx``."""
        instruments = []
        for inst in external.portfolio.instruments:
            if isinstance(inst, LocalCurrencyNonResidentInstrument) and inst.years:
                years = list(inst.years)
                pa = fx_pa.reindex(years).ffill().bfill()
                eop = fx_eop.reindex(years).ffill().bfill()
                instruments.append(
                    replace(
                        inst,
                        fx_pa=[float(pa.loc[y]) for y in years],
                        fx_eop=[float(eop.loc[y]) for y in years],
                    )
                )
            else:
                instruments.append(inst)
        return ExternalDebtBook(
            portfolio=PVPortfolio(instruments=tuple(instruments)),
            inputs=replace(external.inputs, fx_pa=fx_pa, fx_eop=fx_eop),
        )


__all__ = ["ExternalPortfolioAdjuster"]

"""Immutable workbook evaluation context for stress runners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook
from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.scenario.customized import CustomizedScenarioSpec
from lic_dsf.stress.tailored_params import TailoredParams
from lic_dsf.stress.types import Input6StandardParams


@dataclass(frozen=True, slots=True)
class StressContext:
    """Immutable anchor for one LIC-DSF workbook stress evaluation.

    Holds baseline books and Input 6/7 parameters. Does not compute shocks or
    ratios — runners consume this context in later phases.
    """

    macro: MacroDebtBook
    external: ExternalDebtBook
    ext_base: BaselineExternalBook
    pub_base: BaselinePublicBook
    input6: Input6StandardParams
    residual: ResidualFinancingParams
    tailored: TailoredParams | None = None
    market_access: bool = False
    custom_spec: CustomizedScenarioSpec | None = None

    @classmethod
    def from_workbook(cls, path: str | Path) -> StressContext:
        """Load core books plus Input 6/7/tailored and Input 1 market access."""
        from lic_dsf.load.core import load_core
        from lic_dsf.load.input6 import load_input6_standard
        from lic_dsf.load.input7 import load_input7_residual_params
        from lic_dsf.load.rating import load_input1_market
        from lic_dsf.load.tailored import load_customized_spec, load_tailored_params

        workbook = Path(path)
        macro, external, ext_base, pub_base = load_core(workbook)
        market_access, _embi = load_input1_market(workbook)
        return cls(
            macro=macro,
            external=external,
            ext_base=ext_base,
            pub_base=pub_base,
            input6=load_input6_standard(workbook),
            residual=load_input7_residual_params(workbook),
            tailored=load_tailored_params(workbook),
            market_access=bool(market_access),
            custom_spec=load_customized_spec(workbook),
        )

    @classmethod
    def from_parts(
        cls,
        macro: MacroDebtBook,
        external: ExternalDebtBook,
        input6: Input6StandardParams,
        residual: ResidualFinancingParams,
        *,
        market_access: bool = False,
        tailored: TailoredParams | None = None,
        custom_spec: CustomizedScenarioSpec | None = None,
        ext_base: BaselineExternalBook | None = None,
        pub_base: BaselinePublicBook | None = None,
    ) -> StressContext:
        """Build a context from already-loaded books (no workbook path)."""
        return cls(
            macro=macro,
            external=external,
            ext_base=ext_base or BaselineExternalBook(macro=macro, external=external),
            pub_base=pub_base or BaselinePublicBook(macro=macro, external=external),
            input6=input6,
            residual=residual,
            tailored=tailored,
            market_access=bool(market_access),
            custom_spec=custom_spec,
        )

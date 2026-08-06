"""Python implementation of the IMF/World Bank LIC-DSF Excel template.

``lic_dsf.pv`` is the first submodule: present-value instruments (``PV_Base``,
``PV_LC_NR``), portfolios, Ext_Debt book / existing-debt inputs, and workbook
loaders. Additional sheets (Macro-Debt, Chart Data, …) will land as sibling
packages under ``lic_dsf`` as coverage grows.
"""

from __future__ import annotations

__version__ = "0.1.0"

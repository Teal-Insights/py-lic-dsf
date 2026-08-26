"""LIC-DSF DSA layer: baseline sustainability ratios (and later ratings).

Consumes ``lic_dsf.pv`` Macro / Ext books; does not own present-value instrument
math. Standard stress tests live in ``lic_dsf.stress``. Output DataFrames live
in ``lic_dsf.output``.
"""

from lic_dsf.dsa.baseline import BaselineExternalBook, BaselinePublicBook
from lic_dsf.dsa.workbook import load_core

__all__ = [
    "BaselineExternalBook",
    "BaselinePublicBook",
    "load_core",
]

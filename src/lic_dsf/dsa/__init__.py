"""LIC-DSF DSA layer: baseline sustainability ratios (and later ratings).

Consumes ``lic_dsf.pv`` Macro / Ext books; does not own present-value instrument
math. Standard stress tests live in ``lic_dsf.stress``. Workbook loaders live
in ``lic_dsf.load``. Output DataFrames live in ``lic_dsf.output``.
"""

from lic_dsf.dsa.baseline import BaselineExternalBook, BaselinePublicBook

__all__ = [
    "BaselineExternalBook",
    "BaselinePublicBook",
]

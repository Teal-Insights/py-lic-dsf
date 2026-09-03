"""Probe catalogs for Output-panel differential tests."""

from tests.parity.catalogs.bsheet_external import bsheet_external_probes
from tests.parity.catalogs.bsheet_public import bsheet_public_probes
from tests.parity.catalogs.output_1 import output_11_probes, output_12_probes
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes
from tests.parity.catalogs.output_5 import (
    output_7_probes,
    output_51_probes,
    output_52_probes,
)
from tests.parity.catalogs.resfin import resfin_probes

__all__ = [
    "bsheet_external_probes",
    "bsheet_public_probes",
    "output_7_probes",
    "output_11_probes",
    "output_12_probes",
    "output_31_probes",
    "output_32_probes",
    "output_51_probes",
    "output_52_probes",
    "resfin_probes",
]

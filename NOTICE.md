# Notice on the bundled workbook

This repository bundles Excel files under `data/`:

- `lic-dsf-template-2025-08-12.xlsm` — official macro-enabled LIC-DSF template
- `lic-dsf-template-2025-08-12.xlsx` — macros-stripped copy used by loaders and tests

Those files are the **Low-Income Country Debt Sustainability Framework (LIC-DSF)
template**, a joint work of the **International Monetary Fund** and the **World
Bank**. They are published by those institutions and distributed to country
authorities. They are included here **unmodified** (aside from macros stripping
for the `.xlsx`), so Python parity work can be reproduced against the exact
bytes. Provenance and checksums are in `data/PROVENANCE.md`.

Copyright in the workbook rests with the IMF and the World Bank. Including it
here is not a claim of ownership and does not transfer any rights in it. If you
intend to reuse the template itself, obtain it from, and follow the terms of,
the official sources listed in `data/PROVENANCE.md`.

The **MIT license** in `LICENSE` covers only the Python source code in this
repository, not the workbook.

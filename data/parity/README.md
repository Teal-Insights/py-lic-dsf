# Parity JSON cases

Excel-oracle differential cases for `lic_dsf`. Each directory under `cases/` holds:

| File | Role |
|---|---|
| `case.json` | Case id, workbook path, cell overlays, probe catalog filters |
| `expected.json` | Oracle-minted probe goldens (`oracle.excel_build` is `cached`, `grapher`, or `live`) |

## Mint (oracle only — never the Python SUT)

```bash
# Bootstrap / Linux: last-saved cached values from the bundled .xlsx
uv run python -m tests.parity.mint --all --source cached

# Fast proxy oracle (excel-grapher FormulaEvaluator; install grapher extra)
uv sync --extra grapher
uv run python -m tests.parity.mint --case template-baseline-output11 --source grapher
uv run python -m tests.parity.mint --case overlay-fx50-output31 --source grapher

# Windows + Excel: live calculate (authoritative for spreadsheet-identity claims)
LIC_DSF_EXCEL=1 uv run python -m tests.parity.mint --case template-baseline-output11 --source live
```

`grapher` is cheaper than live Excel and supports overlays (surgical XLSX patch then evaluate). Stamp is `excel_build: "grapher"` — a proxy oracle, not Microsoft Excel. Prefer `live` when publishing the identity claim, especially if OFFSET/INDIRECT caches may freeze stress intermediates.

On this WSL2 host, live mint uses the Windows Python + xlwings venv (Excel COM cannot run inside Linux):

```bash
# from WSL — drives C:\Users\Sravan\.venvs\lic-dsf-win against the WSL repo
/mnt/c/Users/Sravan/.venvs/lic-dsf-win/Scripts/python.exe -c "
import os, sys
from pathlib import Path
repo = Path(r'\\\\wsl.localhost\\Ubuntu\\home\\sravan\\py-lic-dsf')
os.chdir(repo); os.environ['LIC_DSF_EXCEL']='1'
sys.path[:0] = [str(repo/'src'), str(repo)]
from tests.parity.mint import main
raise SystemExit(main(['--all', '--source', 'live']))
"
```

Mint never calls the Python SUT. After minting, `case.json` / `expected.json` carry `oracle.minted_at` and `template_sha`.

Suggested Output 3-1 / 3-2 overlay inputs: [`OUTPUT_3_INPUT_CATALOG.md`](OUTPUT_3_INPUT_CATALOG.md).

## Run

```bash
uv run pytest tests/test_parity_cases.py
uv run python -m tests.parity.report
```

Equality uses `tests.parity.equality` (`ABS_TOL=1e-6`, `REL_TOL=1e-12`).

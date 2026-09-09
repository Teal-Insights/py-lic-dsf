"""Unit tests for parity JSON case schema and overlays (no full DSA load)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.parity.case_schema import (
    CellOverlay,
    decode_sut_key,
    encode_sut_key,
    load_case,
    load_expected,
)
from tests.parity.catalog_registry import known_catalogs
from tests.parity.overlays import materialize_workbook, parse_a1


def test_parse_a1_and_sut_key_roundtrip() -> None:
    assert parse_a1("N30") == (30, 14)
    assert parse_a1("AA1") == (1, 27)
    key = ("B1_GDP", 35, 2024)
    assert decode_sut_key(encode_sut_key(key)) == key


def test_load_case_template_output11() -> None:
    case = load_case(
        Path(__file__).resolve().parents[1]
        / "data"
        / "parity"
        / "cases"
        / "template-baseline-output11"
    )
    assert case.id == "template-baseline-output11"
    assert case.probes.catalog == "output_11"
    assert case.probes.years is not None
    assert 2024 in case.probes.years
    assert case.workbook_path().is_file()


def test_known_catalogs_include_baseline() -> None:
    names = known_catalogs()
    assert "output_11" in names
    assert "output_31" in names
    assert "bsheet_ext" in names


def test_overlay_write_roundtrip(tmp_path: Path) -> None:
    from fastpyxl import load_workbook

    repo = Path(__file__).resolve().parents[1]
    src = repo / "data" / "lic-dsf-template-2025-08-12.xlsx"
    dest = tmp_path / "patched.xlsx"
    materialize_workbook(
        src,
        (
            CellOverlay(
                sheet="Input 1 - Basics",
                cell="A1",
                value="parity-overlay-marker",
            ),
        ),
        dest=dest,
    )
    wb = load_workbook(dest, data_only=False, read_only=True)
    try:
        assert wb["Input 1 - Basics"].cell(1, 1).value == "parity-overlay-marker"
    finally:
        wb.close()


def test_load_expected_requires_object(tmp_path: Path) -> None:
    path = tmp_path / "expected.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="JSON object"):
        load_expected(path)


def test_presets_expand_and_unknown_fails() -> None:
    from tests.parity.presets import expand_presets, known_presets

    assert "higher_fx_shock" in known_presets()
    overlays = expand_presets(("higher_fx_shock",))
    assert len(overlays) >= 2
    assert any(o.cell == "D38" and o.value == 50.0 for o in overlays)
    assert any(o.cell == "D58" and o.value == 50.0 for o in overlays)
    with pytest.raises(KeyError, match="unknown overlay preset"):
        expand_presets(("not_a_real_preset",))


def test_new_overlay_presets_expand_without_keyerror() -> None:
    """Catalog §E wave presets must be registered and expand cleanly."""
    from tests.parity.presets import expand_presets, known_presets

    names = (
        "larger_transfers_shock",
        "larger_fdi_shock",
        "weaker_fx_passthrough",
        "higher_inflation_elasticity",
        "higher_exports_gdp_elasticity",
        "higher_market_fx",
        "weaker_market_fx_passthrough",
        "shorter_market_maturity_cap",
        "more_severe_commodity_price",
        "higher_resfin_domestic_st_share",
        "higher_resfin_external_interest",
        "larger_cl_shock",
    )
    known = set(known_presets())
    for name in names:
        assert name in known
        assert len(expand_presets((name,))) >= 1


def test_case_resolved_overlays_include_presets() -> None:
    case = load_case(
        Path(__file__).resolve().parents[1]
        / "data"
        / "parity"
        / "cases"
        / "overlay-fx50-output31"
    )
    assert case.inputs.presets == ("higher_fx_shock",)
    resolved = case.inputs.resolved_overlays()
    assert any(o.cell == "D38" and o.value == 50.0 for o in resolved)


def test_grapher_available_and_reads_one_probe() -> None:
    from tests.parity.grapher import grapher_available, read_grapher_output
    from tests.parity.probes import Probe

    if not grapher_available():
        pytest.skip("excel-grapher / fastpyxl>=1.1 not installed")
    repo = Path(__file__).resolve().parents[1]
    probes = (
        Probe(
            sheet="Output 1-1 - External DSA",
            row=30,
            col=16,  # P
            year=2024,
            sut_key=30,
            label="PV/GDP",
        ),
    )
    frame = read_grapher_output(
        repo / "data" / "lic-dsf-template-2025-08-12.xlsx",
        probes,
    )
    assert len(frame) == 1
    assert isinstance(frame.loc[0, "excel_value"], (int, float))


def test_case_json_rejects_bad_catalog_shape(tmp_path: Path) -> None:
    case_dir = tmp_path / "bad"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "id": "bad",
                "workbook": "data/lic-dsf-template-2025-08-12.xlsx",
                "probes": {"catalog": 1},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="catalog"):
        load_case(case_dir)

"""Unit tests for C4 market-term shortening (Phase 13)."""

from __future__ import annotations

from lic_dsf.stress.market_terms import shorten_loan_terms


def test_shorten_maturity_above_cap_becomes_cap() -> None:
    terms = shorten_loan_terms(
        original_maturity=12.0,
        original_grace=9.0,
        maturity_cap=5.0,
        maturity_factor=2.0 / 3.0,
        grace_factor=2.0 / 3.0,
    )
    assert terms.maturity_rounded == 5
    assert terms.grace_rounded == 3
    assert terms.bullet is False


def test_shorten_maturity_at_or_below_cap_scales() -> None:
    terms = shorten_loan_terms(
        original_maturity=5.0,
        original_grace=1.0,
        maturity_cap=5.0,
        maturity_factor=2.0 / 3.0,
        grace_factor=2.0 / 3.0,
    )
    assert terms.maturity_rounded == 3
    assert terms.grace_rounded == 1


def test_shorten_bullet_grace_is_maturity_minus_one() -> None:
    terms = shorten_loan_terms(
        original_maturity=12.0,
        original_grace=11.0,
        maturity_cap=5.0,
        maturity_factor=2.0 / 3.0,
        grace_factor=2.0 / 3.0,
    )
    assert terms.bullet is True
    assert terms.grace_rounded == terms.maturity_rounded - 1

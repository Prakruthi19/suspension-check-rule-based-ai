from __future__ import annotations

import json

import pytest

from dueproc.cli import main

from .conftest import EXAMPLES

EXPECTED_FLAGS = {
    # Gate 2 scenario (a): two-day suspension with no written notice.
    "scenario_a_two_day_no_notice": {
        "IL-01",
        "IL-02",
        "IL-03",
        "IL-04",
        "IL-07",
        "IL-09",
        "IL-15",
        "IL-16",
    },
    # Gate 2 scenario (b): seven-day suspension, IEP, cumulative removals reach twelve days.
    "scenario_b_iep_cumulative_twelve": {
        "IL-04",
        "IL-05",
        "IL-08",
        "IL-09",
        "IL-15",
        "IL-16",
        "FED-01",
        "FED-02",
        "FED-03",
        "FED-09",
    },
    # Gate 2 scenario (c): expulsion recommendation with a hearing notice.
    "scenario_c_expulsion_hearing": {"IL-05", "IL-15", "IL-16"},
}


@pytest.mark.parametrize("name", sorted(EXPECTED_FLAGS))
def test_gate2_scenarios(name, capsys):
    assert main(["check", str(EXAMPLES / f"{name}.json"), "--today", "2026-09-27", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert {f["rule_id"] for f in out["flags"]} == EXPECTED_FLAGS[name]
    assert out["disclaimer"] and out["resources"]


def test_text_output(capsys):
    main(
        ["check", str(EXAMPLES / "scenario_b_iep_cumulative_twelve.json"), "--today", "2026-09-27"]
    )
    out = capsys.readouterr().out
    assert "TIMELINE" in out and "FED-02" in out and "not legal advice" in out
    assert "2026-10-06" in out


def test_invalid_facts_exit_code(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text('{"incident_date": "nope"}')
    assert main(["check", str(p)]) == 2


def test_rules_listing(capsys):
    main(["rules"])
    out = capsys.readouterr().out
    assert out.count("pending review") == 26

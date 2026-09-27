from __future__ import annotations

import json
from pathlib import Path

import pytest

from dueproc.calendar import SchoolCalendar

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="session")
def cps() -> SchoolCalendar:
    return SchoolCalendar.default()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

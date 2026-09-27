"""Letters assembled from the flags that fired.

Early spike (Week 2): only the suspension review request (Appendix F), as plain
text. DOCX, printable HTML, and the other three variants are Week 3 work.
Fill-in fields the survey does not collect stay as [brackets] for the parent.
"""

from __future__ import annotations

from datetime import date

from jinja2 import Environment, PackageLoader, StrictUndefined

from dueproc.facts import Facts, NoticeReceived, RemovalKind
from dueproc.rules import Flag

_env = Environment(
    loader=PackageLoader("dueproc.letters", "templates"),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,  # plain-text output; HTML rendering escapes separately
)

_KIND_PHRASE = {
    RemovalKind.OSS: "out-of-school suspension",
    RemovalKind.ISS: "in-school suspension",
    RemovalKind.BUS: "bus suspension",
    RemovalKind.INFORMAL: "removal from school (my child was sent home)",
    RemovalKind.EXPULSION: "recommended expulsion",
    RemovalKind.ALTERNATIVE: "transfer to an alternative school",
    RemovalKind.OTHER: "disciplinary removal",
}


def _join_or(items: list[str]) -> str:
    if len(items) <= 2:
        return " or ".join(items)
    return ", ".join(items[:-1]) + ", or " + items[-1]


_env.filters["join_or"] = _join_or


def _long(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def review_request(facts: Facts, flags: list[Flag], today: date | None = None) -> str:
    fired = {f.rule_id for f in flags}
    r = facts.removal
    return _env.get_template("review_request.txt.j2").render(
        today=_long(today or date.today()),
        kind=_KIND_PHRASE[r.kind],
        days=r.school_days,
        decision_date=_long(r.decision_date),
        cumulative=facts.cumulative_days,
        fired=fired,
        written_notice=facts.notice.received is NoticeReceived.WRITTEN,
        notice_defects=bool(fired & {"IL-01", "IL-03", "IL-04", "IL-05"}),
        missing=[
            text
            for rid, text in (
                ("IL-01", "the reasons for the suspension"),
                ("IL-03", "the specific act of gross disobedience or misconduct"),
                ("IL-04", "the rationale for the length of the suspension"),
                (
                    "IL-05",
                    "whether other appropriate and available interventions were attempted "
                    "before a suspension longer than three days was imposed",
                ),
            )
            if rid in fired
        ],
        threat_finding="IL-06" in fired or "IL-07" in fired,
        idea="FED-02" in fired or "FED-03" in fired,
        basis_of_knowledge="FED-07" in fired,
        section_504="FED-08" in fired,
        records="IL-15" in fired,
        support_services="IL-08" in fired,
        makeup_work="IL-09" in fired,
    )

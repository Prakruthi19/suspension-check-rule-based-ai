# Threat model (one page)

Scope: the alpha service (`app/api/main.py`, `app/web/`) and the library it
calls. Assets worth protecting: what a family types, what a discipline log
contains, and the service's availability. The service stores nothing, so there
is no database to steal; the risks are leaks in transit, in logs, in outputs,
and denial of service.

| # | What an attacker could try | What stops it | Checked by |
|---|---|---|---|
| 1 | Read another family's answers | Nothing is stored; each request is evaluated in memory and discarded | `tests/test_no_persistence.py` (no storage imports, no file writes in `src/` or `app/`) |
| 2 | Find identifying text in logs | Allowlist log line only; uvicorn access log disabled in code; descriptions redacted before validation | `test_logs_never_contain_request_body`, `test_uvicorn_access_log_is_off` |
| 3 | Upload a log and read names or IDs back | Names and unmapped columns dropped unread; IDs become salted HMACs; error messages name rows and columns, never values; free-text labels under 10 rows merged into "Other or unlisted" | `test_names_and_ids_never_appear_in_output`, `test_free_text_labels_cannot_surface_as_groups`, `test_error_messages_never_echo_cell_values` |
| 4 | Identify a child through a small group | No count under 10 shown, no rate or ratio from a group under 10, monthly and grade cells suppressed | Hypothesis property `test_no_cell_under_threshold_is_ever_shown` |
| 5 | Crafted header or formula (CSV injection, `=HYPERLINK`) | Outputs are aggregates; headers are shown as escaped text; XLSX read with `data_only=True`, so formulas are never evaluated | `test_xlsx_formulas_are_not_evaluated_or_echoed`, `test_brief_html_is_one_escaped_page` |
| 6 | Zip bomb disguised as XLSX | Upload capped at 2 MB; workbook refused if it unpacks past 40 MB; rows capped at 20,000 and columns at 60 | `test_xlsx_zip_bomb_is_refused`, `test_size_and_row_limits` |
| 7 | Oversized or malformed body | 32 KB cap (2 MB for Pattern Check); missing or malformed `Content-Length` refused before the body is read | `test_body_limit`, `test_pattern_upload_limit_is_larger_but_bounded`, `test_malformed_content_length_is_rejected_not_a_crash` |
| 8 | Flood of requests | 30 requests per minute per client, in memory; behind a proxy, counted by `X-Forwarded-For` when trusted | `test_rate_limit`, `test_rate_limit_uses_forwarded_client_only_when_trusted` |
| 9 | Script injection into the page or the brief | Pages build the DOM with `textContent`-style APIs; brief and letters escape every value; CSP allows same-origin only | `test_brief_html_is_one_escaped_page`, `test_security_headers` |
| 10 | Embedding the page to trick a parent | `X-Frame-Options: DENY` | `test_security_headers` |
| 11 | Vulnerable dependency | `pip-audit` in CI on every push | CI "Dependency audit" step |
| 12 | Misleading legal output | Every rule labelled "pending legal review" until reviewed; disclaimer and resource card on every output | `rules` command; letter goldens |

## Known gaps

- **Rate limiting is per process.** With several instances, each counts
  separately. Fine for the alpha; use the host's rate limiting if scaled out.
- **The hosting platform's own logs** may record addresses. Choose a host that
  can turn them off (see `docs/deploy.md`).
- **`X-Forwarded-For` can be forged** if `SUSPENSION_CHECK_TRUST_PROXY=1` is
  set without a proxy in front. The Docker image assumes a proxy.
- **CSP allows inline scripts and styles** because the pages have no build step.
  Moving scripts to files would allow a stricter policy.
- **Not yet verified on a deployed URL.** Limits and headers are tested in CI
  and in the container locally (2026-10-23), not yet on a public host.

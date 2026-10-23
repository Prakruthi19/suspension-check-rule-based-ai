# Privacy

Suspension Check is built so that there is nothing to leak. This page says
exactly what the server sees, for how long, and what it writes down.

## What the server receives

| Request | What is in it | Size limit |
|---|---|---|
| `POST /api/check`, `/api/letter`, `/api/calendar` | The survey answers as JSON: dates, numbers of days, Yes / No / Not sure answers, and an optional one-or-two-sentence description | 32 KB |
| `POST /api/pattern/*` (Pattern Check) | A discipline log (CSV or XLSX) and optional enrollment counts | 2 MB, 20,000 rows |

The survey never asks for the student's name, school, or ID. The web page fills
letters with `[brackets]` that the parent completes on their own device.

## What happens to it

1. **Redaction first.** The free-text description passes through redaction
   (`src/suspension_check/redact.py`) before validation, before the rules, and
   before anything could log it. Names, phone numbers, emails, street
   addresses, student ID numbers, and SSNs become placeholders such as
   `<PERSON>`.
2. **Pattern Check drops identifying columns.** Name columns are dropped on
   read. A student ID column is replaced by a salted hash used only to count
   repeat suspensions; the salt is random per request and is never kept, so the
   hash cannot be matched across requests. Every other unmapped column is
   discarded unread.
3. **Evaluated in memory.** Rules, timeline, letters, and files are built in
   memory and returned in the response.
4. **Discarded.** When the response is sent, the request is gone. There is no
   database, no file storage, no cache, no queue, and no storage credentials.
   A test (`tests/test_no_persistence.py`) fails CI if any module in `src/` or
   `app/` imports a storage library or writes a file.

## What is logged

One line per request, from an allowlist:

```
rid=1f7453c5a629 path=/api/check status=200 ms=25.9 rules=IL-04,IL-05,FED-02
```

That is a random request ID, the path, the status code, the time taken, and
which rule IDs fired. Never a request body, never a description, never a
client address. Uvicorn's own access log (which would record addresses) is
switched off in code, and a test checks that it stays off.

## Addresses and rate limiting

To stop floods, the server counts requests per client address in memory for at
most 60 seconds. The addresses are never written anywhere. Behind a reverse
proxy, `SUSPENSION_CHECK_TRUST_PROXY=1` makes the count use the visitor's
address from `X-Forwarded-For` instead of the proxy's.

## In the browser

The page keeps the answers in the page's memory only. It uses no cookies, no
`localStorage`, no analytics, and no third-party scripts or fonts. Downloads
(Word, HTML, `.ics`) are created as blobs and saved by the browser.

## Headers

Every response carries `Cache-Control: no-store`, a strict
`Content-Security-Policy` (same origin only), `Referrer-Policy: no-referrer`,
`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS, and a
`Permissions-Policy` that turns off camera, microphone, and location.

## What we cannot promise

The hosting provider can see that a connection was made, and its own platform
logs may record addresses. Choose a host that lets you turn those off or keeps
them briefly (see `docs/deploy.md`). Once a parent downloads a letter, that file
is theirs; we have no copy.

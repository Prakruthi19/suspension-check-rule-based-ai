# Deploying the alpha

The service is one stateless container. It needs no volume, no database, and
no secrets.

## Build and run

```bash
docker build -t suspension-check .
docker run --rm -p 8000:8000 --read-only --tmpfs /tmp suspension-check
# open http://127.0.0.1:8000
```

Checked on 2026-10-23: the image builds, runs as a non-root user on a
read-only filesystem, answers `/api/health`, redacts a description (the spaCy
model is baked into the image), and logs only the allowlist line.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Port to listen on (most hosts set this) |
| `SUSPENSION_CHECK_ALLOWED_ORIGINS` | empty | Comma-separated origins allowed to call the API from another site. Leave empty when the page and API share one URL (the normal case) |
| `SUSPENSION_CHECK_RATE_LIMIT` | `30` | Requests per minute per visitor |
| `SUSPENSION_CHECK_TRUST_PROXY` | `1` in the image | Count rate limits by the visitor's `X-Forwarded-For` address. Set to `0` if the container is exposed directly |

## Hosts

Any host that runs a Dockerfile over HTTPS works (Render, Fly.io, Railway,
Google Cloud Run). Before choosing, check that:

1. HTTPS is on by default.
2. Platform request logs can be turned off or are kept for a short time.
3. No disk is attached (do not add a volume).

## Pre-launch checklist

- [ ] HTTPS URL loads; `/api/health` returns `ok` and the expected version.
- [ ] A Gate 2 scenario runs end to end on the deployed URL.
- [ ] Platform logs show only `rid=... path=... status=...` lines.
- [ ] No volume, database, or storage credential is attached to the service.
- [ ] The 31st request in a minute from one browser gets a 429.

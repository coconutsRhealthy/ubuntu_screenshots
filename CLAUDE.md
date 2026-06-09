# ubuntu_screenshots — project & server architecture

Read this first. It describes what this project is, the droplet it runs on, and
how it relates to the second half of the system. For step-by-step deploy / build
/ redeploy commands see **DEPLOY.txt**.

## What this project does

A webshop **screenshot collector**. It loads a list of ~148 Dutch webshops from a
JSON file in Cloudflare R2, and once per shop per day takes a headless-Chromium
screenshot and uploads it as JPEG to the R2 `screenshots` bucket.

- `screenshot.py` — `run_cycle()`: one full pass (load list → find which shops are
  due → screenshot each due shop → upload to R2). The actual scraping logic
  (Chrome options, cookie-banner handling, JPEG encode) — unchanged from the
  original `working_chromium.py`; only restructured.
- `collect.py` — the container's main process: a `while True` loop that runs one
  cycle, logs a status line, sleeps `POLL_HOURS` (default 1h), repeats forever.
- `Dockerfile` — python:3.11-slim + chromium + chromium-driver.

## The bigger system: producer → consumer

This project is the **producer** half. There is a separate **consumer**:

```
ubuntu_screenshots (THIS repo)                image_openai  (separate repo)
container: screenshot-bot                     container: eije2
  loads webshop list (R2 JSON)                  loads the SAME webshop JSON
  screenshots each shop          ── R2 ──►      reads screenshots from R2
  uploads JPEG → R2 "screenshots"               compares latest vs previous per shop
                                                if changed → OpenAI promo detection
                                                → R2 "promotions" bucket + Telegram
                                                loops hourly + runs a Telegram bot
```

- **image_openai** repo: `github.com/coconutsRhealthy/image_openai`, deployed from
  branch `claude_whs` (its Dockerfile git-clones that branch at build time).
- They share the R2 `screenshots` bucket and the same webshop list JSON.
- **If you stop screenshot-bot, eije2 keeps running but has no fresh images to
  compare.** They are coupled; don't stop the producer without knowing this.

## The droplet

- DigitalOcean droplet, hostname `ubuntu-s-1vcpu-1gb-ams3-01`, region AMS3.
- IP `165.22.205.11`, ssh as `root` (key auth).
- Specs: **1 vCPU, 1 GB RAM**, 24 GB disk. This box is resource-constrained — it
  is the dominant design constraint for everything here.
- **Swap: 2 GB** `/swapfile` (in `/etc/fstab`), `vm.swappiness=10`
  (`/etc/sysctl.d/99-swappiness.conf`). Added 2026-06-09 — there was none before.

### Containers on the droplet

| Container | Repo | Host dir | Role | Restart policy |
|-----------|------|----------|------|----------------|
| `screenshot-bot` | this repo | `/root/screenshot-bot` | screenshot producer | `unless-stopped` |
| `eije2` | image_openai | (built from GitHub) | promo-detection consumer | `no` |

Note: `eije2` has restart policy **`no`** — it will NOT come back on its own after
a crash or droplet reboot. Worth fixing to `unless-stopped` if you ever rebuild it.

## How the resource constraints are handled (the 1 GB / 1 vCPU box)

The original setup paid for these constraints with a fragile workaround; the
current setup addresses them directly:

- **Memory** — Chromium leaks across page loads. We launch + quit a **fresh
  Chromium per shop**, so peak memory stays bounded to one Chrome on one page
  instead of growing across the run. Swap is the safety net underneath that.
- **CPU** — the dominant old cost was *container churn* (see history below), now
  gone. Relaunch the container with `--cpus="0.7"` so Chromium can't pin the one
  core (this matches the value the old watchdog used).
- **Crashes / reboots** — `docker run --restart unless-stopped` is the entire
  supervision strategy. No watchdog, no systemd unit.

## History — what changed and why (2026-06-09)

The original deploy was a **one-shot** `screenshot.py` plus an external
`screenshot-watchdog.sh` run as a systemd service (`screenshot-watchdog.service`).
The watchdog relaunched a fresh container ~120×/day (~every 6–7 min) and
force-killed each one after 30 min — because a long-lived Chromium would OOM the
1 GB box. That constant create/render/destroy churn is what kept CPU near 100%.

Replaced with the long-running-container pattern used by the sibling projects
`claude_funda` and `claude_birdeye_trending`: the script is its own hourly
scheduler, Chromium is recycled per shop, Docker's restart policy is the backstop.
Same screenshot output (~1/shop/day via the 24h dedupe), ~5× less Chromium churn.

Removed: `screenshot-watchdog.service` (systemd unit + unit file) and
`screenshot-watchdog.sh`. Also removed unrelated cruft (Bybit code, old
Firebase/Firefox `make_screenshots.py`, etc.) — see git history.

## Secrets

R2 credentials live in `/root/screenshot-bot/.env` on the droplet (mode 600), NOT
in git (`.env` is gitignored). The R2 account is shared with eije2. eije2
additionally holds an OpenAI key and a Telegram bot token in its own container env.

## Current state (2026-06-09)

- New code built and deployed to the droplet; all paths verified (Chromium, R2,
  a real end-to-end screenshot+upload of one shop).
- **`screenshot-bot` is currently STOPPED (parked)** at the operator's request —
  do NOT relaunch without an explicit OK. To start it, see DEPLOY.txt
  ("DEPLOY COMMANDS"); use the `--cpus="0.7"` form.
- `eije2` is running untouched.
- Swap added; watchdog fully removed.

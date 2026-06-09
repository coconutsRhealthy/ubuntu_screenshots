"""Long-running scheduler — the container's main process. See DEPLOY.txt.

Runs one screenshot cycle, logs a status line, sleeps POLL_HOURS, repeats
forever. A failed cycle is logged and the loop continues; Docker's
`--restart unless-stopped` is the backstop if the process itself dies. This
replaces the old screenshot-watchdog.sh + systemd unit entirely.
"""

import logging
import os
import time

from screenshot import run_cycle

POLL_HOURS = float(os.environ.get("POLL_HOURS", "1"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info(f"Screenshot collector starting — cycle every {POLL_HOURS}h")
    while True:
        logger.info("Starting screenshot cycle")
        try:
            shot, skipped, failed = run_cycle()
            logger.info(
                f"ok  cycle done  shot:{shot} skipped:{skipped} failed:{failed}"
            )
        except Exception as e:
            logger.error(f"cycle failed: {e}")

        logger.info(f"Sleeping {POLL_HOURS}h")
        time.sleep(POLL_HOURS * 3600)

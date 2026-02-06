import threading
import time
import logging
from trainer.ae.train_incremental import train_incremental
from pathlib import Path
import json

log = logging.getLogger("scheduler")

INTERVAL_SECONDS = 3 * 60 * 60  # 3 hours
STATE_FILE = Path("models/experiments/ae/training_state.json")

INTERVAL_SECONDS = 3 * 60 * 60  # 3 hours
STATE_FILE = Path("models/experiments/ae/training_state.json")

def update_next_run():
    try:
        state = {}
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())

        state["next_scheduled_at"] = time.time() + INTERVAL_SECONDS
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass

def should_train():
    if not STATE_FILE.exists():
        return True

    try:
        state = json.loads(STATE_FILE.read_text())
        return state.get("status") not in ("running",)
    except Exception:
        return True


def scheduler_loop():
    log.info("🕒 AE scheduler started")
    update_next_run()

    while True:
        time.sleep(INTERVAL_SECONDS)

        try:
            update_next_run()

            if should_train():
                log.info("⏱ Triggering scheduled incremental training")
                train_incremental()
            else:
                log.info("⏸ Training already running, skipping")

        except Exception as e:
            log.exception("Scheduled training failed: %s", e)

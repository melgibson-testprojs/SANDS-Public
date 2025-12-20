import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "swarmsec_ids.log")

def get_ids_logger():
    logger = logging.getLogger("swarmsec_ids")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger  # prevent duplicate handlers

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

IDS_LOG_PATH = os.path.join(LOG_DIR, "swarmsec_ids.log")
SERVER_LOG_PATH = os.path.join(LOG_DIR, "swarmsec_server.log")


# ---------------------------------------------------
# IDS / PREDICTION LOGGER (EXISTING NAME, NEW ROLE)
# ---------------------------------------------------
def get_ids_logger():
    """
    IDS prediction logger.
    Use ONLY for ML / fusion decisions.
    """
    logger = logging.getLogger("swarmsec_ids")

    if logger.handlers:
        return logger  # prevent duplicate handlers

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        IDS_LOG_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.propagate = False

    return logger


# ---------------------------------------------------
# GENERAL SERVER LOGGER (NEW)
# ---------------------------------------------------
def get_server_logger():
    """
    General server logger.
    Use for startup, errors, validation, heartbeat, etc.
    """
    logger = logging.getLogger("swarmsec_server")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        SERVER_LOG_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.propagate = False

    return logger

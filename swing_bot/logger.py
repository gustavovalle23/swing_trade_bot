import logging
import sys

_initialized = False


def get_logger():
    global _initialized
    log = logging.getLogger("swing_bot")
    if not _initialized:
        log.setLevel(logging.INFO)
        if not log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            log.addHandler(handler)
        _initialized = True
    return log

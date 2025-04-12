import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

def setup_logging():

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "logs/messenger.log")
    log_max_size = int(os.getenv("LOG_MAX_SIZE", 10 * 1024 * 1024))
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))


    os.makedirs(os.path.dirname(log_file), exist_ok=True)


    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)


    logger = logging.getLogger()
    logger.setLevel(log_level)


    for handler in logger.handlers[:]:
        logger.removeHandler(handler)


    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
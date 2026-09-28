import logging
import sys
from logging.handlers import RotatingFileHandler

# Define standard log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Configure custom logger named "hostel_allocation"
logger = logging.getLogger("hostel_allocation")
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(LOG_FORMAT)

# StreamHandler (outputs logs to sys.stdout CMD terminal)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

# RotatingFileHandler (writes to hostel_allocation.log, max 5MB, 3 backup files, UTF-8)
file_handler = RotatingFileHandler(
    "hostel_allocation.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Avoid adding duplicate handlers if logger is imported multiple times
if not logger.handlers:
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
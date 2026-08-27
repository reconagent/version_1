"""
JSON-formatted logging with millisecond precision.
"""
import logging
import json
import time
import sys

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': time.time(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logging():
    """Configure root logger to output JSON to /dev/null or stderr."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)  # will be redirected
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

def get_logger(name):
    return logging.getLogger(name)

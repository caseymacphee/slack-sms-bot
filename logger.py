import logging
import os

log_level = os.environ.get('LOG_LEVEL', logging.DEBUG)
log = logging.getLogger()
log.setLevel(log_level)

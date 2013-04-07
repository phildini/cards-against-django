import logging

log_format = '%(asctime)s %(filename)s:%(lineno)d %(funcName)s %(levelname)s %(message)s'
logging.basicConfig(format=log_format)

logger = logging.getLogger("cah")

logger.setLevel(logging.DEBUG)

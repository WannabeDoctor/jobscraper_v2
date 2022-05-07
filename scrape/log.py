import logging

logger = logging.getLogger("jobscraper")
logger.setLevel(level=logging.INFO)
DATEFMT = "%d-%b-%y %H:%M:%S"
formatter = logging.Formatter("[jobscraper]: %(asctime)s - %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

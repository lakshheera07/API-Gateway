import sys
from loguru import logger


def setup_logging():
    logger.remove()

    logger.add(
        sys.stdout,
        format=(
            '{{'
            '"time":"{time:YYYY-MM-DD HH:mm:ss}",'
            '"level":"{level}",'
            '"message":"{message}",'
            '"request_id":"{extra[request_id]}",'
            '"module":"{module}",'
            '"function":"{function}",'
            '"line":{line}'
            '}}'
        ),
        level="INFO",
    )

    return logger

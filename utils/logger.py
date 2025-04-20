# utils/logger.py

import logging

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance with the given name.

    Args:
        name (str): The name for the logger.

    Returns:
        logging.Logger: The logger instance.
    """
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

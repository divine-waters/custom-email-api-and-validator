import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)

FREE_EMAIL_PROVIDERS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}

async def is_free_provider(email: str) -> bool:
    domain = email.split('@')[-1].lower()

    logger.info(f"Checking if domain {domain} is a free email provider...")

    # Simulate a potentially I/O-bound task
    await asyncio.sleep(0)  # Simulating async behavior

    if domain in FREE_EMAIL_PROVIDERS:
        logger.warning(f"Domain {domain} is a free email provider.")
        return True

    logger.info(f"Domain {domain} is not a free email provider.")
    return False

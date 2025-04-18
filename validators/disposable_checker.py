import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)

DISPOSABLE_DOMAINS = {"mailinator.com", "10minutemail.com", "guerrillamail.com"}

async def is_disposable(email: str) -> bool:
    domain = email.split('@')[-1].lower()

    logger.info(f"Checking if domain {domain} is a disposable email provider...")

    # Simulate a potentially I/O-bound task
    await asyncio.sleep(0)  # Simulating async behavior

    if domain in DISPOSABLE_DOMAINS:
        logger.warning(f"Domain {domain} is a disposable email provider.")
        return True

    logger.info(f"Domain {domain} is not a disposable email provider.")
    return False

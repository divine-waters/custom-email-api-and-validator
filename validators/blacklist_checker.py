import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)

BLACKLISTED_DOMAINS = {"spamdomain.com", "malicious.org"}

async def is_blacklisted(email: str) -> bool:
    domain = email.split('@')[-1].lower()

    logger.info(f"Checking if domain {domain} is blacklisted...")

    # Simulate a potentially I/O-bound task
    await asyncio.sleep(0)  # Simulating async behavior

    if domain in BLACKLISTED_DOMAINS:
        logger.warning(f"Domain {domain} is blacklisted.")
        return True

    logger.info(f"Domain {domain} is not blacklisted.")
    return False

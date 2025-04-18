import asyncio
import aiodns
import tldextract
from utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["check_mx_records"]

INVALID_TLDS = {
    "example", "invalid", "test", "localhost", "local", "onion", "onion.link"
}

TEST_DOMAINS = {
    "example.com", "test.com", "localhost.com", "invalid.com"
}

async def check_mx_records(domain: str):
    extracted = tldextract.extract(domain)
    tld = extracted.suffix

    if tld in INVALID_TLDS:
        logger.warning(f"⚠️ Invalid TLD: {tld}")
        return None

    if domain.lower() in TEST_DOMAINS:
        logger.warning(f"⚠️ Test domain: {domain}")
        return None

    try:
        domain = domain.replace("http://", "").replace("https://", "").replace("www.", "")
        logger.info(f"🔎 Checking MX records for: {domain}")

        resolver = aiodns.DNSResolver(timeout=5)

        response = await asyncio.wait_for(resolver.query(domain, "MX"), timeout=5)

        if not response:
            logger.warning(f"⚠️ No MX records for {domain}")
            return None

        mx_records = [str(rdata.host) for rdata in response]
        logger.info(f"✅ Found MX records for {domain}: {mx_records}")
        return mx_records

    except asyncio.TimeoutError:
        logger.error(f"⏰ Timeout checking MX records for {domain}")
        return None
    except aiodns.error.DNSError as e:
        logger.error(f"⚠️ DNS error for {domain}: {e}")
        return None
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        return None


# Safe test runner
if __name__ == "__main__":
    async def main():
        test_domains = ["yahoo.com", "outlook.com", "example.com", "test.com", "localhost.com", "nonexistentdomain.com"]
        tasks = [check_mx_records(domain) for domain in test_domains]
        results = await asyncio.gather(*tasks)

        for domain, mx_records in zip(test_domains, results):
            if mx_records:
                logger.info(f"MX records for {domain}: {mx_records}")
            else:
                logger.warning(f"No MX records found for {domain} or domain does not exist.")

    asyncio.run(main())
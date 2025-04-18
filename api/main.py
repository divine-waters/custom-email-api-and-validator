import asyncio
from fastapi import FastAPI, Query
from validators.mx_checker import check_mx_records
from validators.disposable_checker import is_disposable
from validators.blacklist_checker import is_blacklisted
from validators.free_provider_checker import is_free_provider
from utils.logger import get_logger

logger = get_logger("main")
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API is up and running!"}

@app.get("/validate-email")
async def validate_email(email: str = Query(...)):
    logger.info(f"🔍 Validating email: {email}")

    domain = email.split('@')[-1].lower()
    logger.info(f"📬 Extracted domain: {domain}")

    logger.info("🔎 Checking MX records...")
    mx_records = await check_mx_records(domain)
    if not mx_records:
        logger.warning(f"❌ No valid MX records found for {domain}")
        return {"error": "No valid MX records found for domain."}
    logger.info(f"✅ MX records for {domain}: {mx_records}")

    logger.info("⚙️ Running additional checks asynchronously...")
    disposable_check, blacklist_check, free_provider_check = await asyncio.gather(
        is_disposable(email),
        is_blacklisted(email),
        is_free_provider(email)
    )

    if disposable_check:
        logger.warning(f"🚫 {email} is a disposable email.")
        return {"error": "Email is from a disposable provider."}
    logger.info(f"✔️ {email} is not a disposable email.")

    if blacklist_check:
        logger.warning(f"🚫 {domain} is blacklisted.")
        return {"error": "Domain is blacklisted."}
    logger.info(f"✔️ {domain} is not blacklisted.")

    if free_provider_check:
        logger.info(f"⚠️ {domain} is a free email provider.")
        return {"warning": "Email is from a free email provider."}
    logger.info(f"✔️ {domain} is not a free email provider.")

    logger.info("🎉 Email passed all checks.")
    return {"message": "Email is valid."}

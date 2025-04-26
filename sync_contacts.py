# sync_contacts.py
from db.email_dao import insert_contacts
from hubspot_client.contacts_client import fetch_all_contacts
from utils.logger import get_logger

logger = get_logger(__name__)

def sync():
    contacts = fetch_all_contacts()
    logger.debug(f"Fetched contacts: {contacts}")
    insert_contacts(contacts)

if __name__ == "__main__":
    sync()

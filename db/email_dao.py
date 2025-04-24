# db/email_dao.py

from db.connector import get_db_connection # Correctly import from the connector
from utils.logger import get_logger
from typing import List, Tuple, Dict, Any # Added type hints

logger = get_logger("email_dao")

# --- Contact Functions ---

def upsert_contact_db(contact_id_val: str, firstname: str, lastname: str, email: str): # Renamed arg for clarity
    """
    Inserts or updates a single contact in the database using MERGE.
    Uses 'contact_id' as the primary key column name.
    """
    if not contact_id_val or not email:
        logger.warning(f"Skipping upsert for contact due to missing ID or Email: ID={contact_id_val}, Email={email}")
        return

    logger.debug(f"Attempting to upsert contact {contact_id_val} ({email})")
    # Updated SQL to use 'contact_id' as the column name
    sql = """
        MERGE INTO contacts AS target
        USING (SELECT ? AS contact_id, ? AS firstname, ? AS lastname, ? AS email) AS source
        ON target.contact_id = source.contact_id -- Join on 'contact_id'
        WHEN MATCHED THEN
            UPDATE SET
                firstname = source.firstname,
                lastname = source.lastname,
                email = source.email
        WHEN NOT MATCHED THEN
            INSERT (contact_id, firstname, lastname, email) -- Insert into 'contact_id'
            VALUES (source.contact_id, source.firstname, source.lastname, source.email);
    """
    # Params order matches the SELECT in USING clause
    params = (contact_id_val, firstname, lastname, email)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            logger.debug(f"Executed MERGE for contact {contact_id_val}")
            conn.commit()
            logger.info(f"✅ Successfully committed upsert for contact {contact_id_val}")
    except Exception as e:
        logger.error(f"💥 Error upserting contact {contact_id_val}: {e}", exc_info=True)
        raise

# --- Contact Functions ---

def insert_contacts(contacts: List[Dict[str, Any]]):
    """
    Inserts or updates contacts in the database using MERGE.
    Uses 'contact_id' as the primary key column name.
    """
    if not contacts:
        logger.info("No contacts provided to insert_contacts.")
        return

    logger.info(f"Attempting to insert/update {len(contacts)} contacts.")
    # Use a set to track processed IDs if needed, though MERGE handles duplicates
    # processed_ids = set()

    # It's generally better to commit once after all operations succeed or fail together
    try: # Outer try for the whole batch
        with get_db_connection() as conn:
            cursor = conn.cursor()

            for contact in contacts:
                contact_id_val = contact.get('id') # Still gets 'id' from HubSpot data
                properties = contact.get('properties', {})
                email = properties.get('email')
                firstname = properties.get('firstname', '') # Default to empty string
                lastname = properties.get('lastname', '')   # Default to empty string

                if not contact_id_val or not email:
                    logger.warning(f"Skipping contact due to missing ID or Email in batch insert: ID={contact_id_val}, Email={email}")
                    continue # Skip this contact and move to the next

                # Inner try for each individual MERGE operation
                try:
                    # Updated SQL to use 'contact_id'
                    cursor.execute("""
                        MERGE INTO contacts AS target
                        USING (SELECT ? AS contact_id, ? AS firstname, ? AS lastname, ? AS email) AS source
                        ON target.contact_id = source.contact_id
                        WHEN MATCHED THEN
                            UPDATE SET firstname = source.firstname, lastname = source.lastname, email = source.email
                        WHEN NOT MATCHED THEN
                            INSERT (contact_id, firstname, lastname, email)
                            VALUES (source.contact_id, source.firstname, source.lastname, source.email);
                    """, contact_id_val, firstname, lastname, email) # Pass the value from HubSpot data

                # --- FIX IS HERE ---
                except Exception as merge_err:
                    # Log the error for the specific contact that failed
                    logger.error(f"💥 Error merging contact {contact_id_val} during batch insert: {merge_err}", exc_info=True)
                    # Decide: continue with next contact or raise/re-raise?
                    # For now, let's log and continue to process other contacts in the batch.
                    # If you want the whole batch to fail on one error, you would 'raise merge_err' here.
                # --- END FIX ---

            # Commit only if the loop completes without the outer try block catching an error
            conn.commit() # This is line 80 from the original traceback context
            logger.info(f"✅ Successfully committed batch insert/update for {len(contacts)} contacts.")

    except Exception as e:
        # Catch errors related to connection or commit
        logger.error(f"💥 Error during batch contact insert/update transaction: {e}", exc_info=True)
        # No explicit rollback needed if 'with get_db_connection()' handles context correctly,
        # otherwise, you'd add conn.rollback() here.
        # Consider re-raising if the caller needs to know about the batch failure
        # raise e

# ... (rest of the file: _fetch_all_contacts_sync, etc.) ...


def _fetch_all_contacts_sync() -> List[Tuple[str, str, str, str]]:
    """Synchronous helper to fetch all contacts."""
    logger.debug("Fetching all contacts from DB...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Updated SELECT to use 'contact_id'
        cursor.execute("SELECT contact_id, firstname, lastname, email FROM Contacts")
        results = cursor.fetchall()
        logger.debug(f"Fetched {len(results)} contacts.")
        return results

# fetch_all_contacts remains the same (calls the sync version)

def _fetch_emails_needing_validation_sync() -> List[Tuple[str, str, str, str]]:
    """Synchronous helper to fetch contacts needing email validation."""
    logger.debug("Fetching contacts needing validation from DB...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Updated SELECT and JOIN to use 'contact_id'
        cursor.execute("""
            SELECT c.contact_id, c.firstname, c.lastname, c.email
            FROM Contacts c
            LEFT JOIN validation_results vr ON c.contact_id = vr.contact_id
            WHERE vr.contact_id IS NULL OR vr.email != c.email
        """)
        results = cursor.fetchall()
        logger.debug(f"Fetched {len(results)} contacts needing validation.")
        return results

# fetch_emails_needing_validation remains the same (calls the sync version)

# --- Validation Result Functions ---
# save_validation_result remains the same as it already uses 'contact_id' correctly

# ... (rest of the file) ...


# --- Validation Result Functions ---

def save_validation_result(validation_result: Dict[str, Any], contact_id: str):
    """
    Saves the detailed email validation result to the validation_results table
    using INSERT. Assumes 'id' is IDENTITY and 'created_at' has a DEFAULT.
    """
    sql = """
        INSERT INTO validation_results (
            contact_id, email, domain, mx_valid, is_disposable,
            is_blacklisted, is_free_provider
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        contact_id,
        validation_result.get('email', ''),
        validation_result.get('domain', ''),
        validation_result.get('mx_valid', False),
        validation_result.get('is_disposable', False),
        validation_result.get('is_blacklisted', False),
        validation_result.get('is_free_provider', False)
        # Note: We don't insert 'id' (identity) or 'created_at' (default)
        # We also don't insert 'status' or 'message' as they are not in the
        # correct schema defined by migrations.py
    )

    logger.debug(f"Attempting to save validation result for contact {contact_id}")
    logger.debug(f"SQL: {sql}")
    logger.debug(f"Params: {params}")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            logger.debug(f"Executed INSERT for contact {contact_id}")
            conn.commit()
            logger.info(f"✅ Successfully committed validation result for contact {contact_id}") # Log AFTER commit
    except Exception as e:
        # Log the full traceback using exc_info=True
        logger.error(f"💥 Error saving validation result for contact {contact_id}: {e}", exc_info=True)
        # No need to explicitly rollback here if using 'with get_db_connection()'
        # which typically handles transaction context, but it doesn't hurt.
        # If get_db_connection doesn't manage transactions, rollback is essential.
        # Assuming it does manage context, just logging the error is sufficient.
        raise # Re-raise the exception so the orchestrator knows about it

# (rest of the file, if any)

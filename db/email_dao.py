# db/email_dao.py

import asyncio
import functools
from db.connector import get_db_connection # Correctly import from the connector
from utils.logger import get_logger
from typing import List, Tuple, Dict, Any # Added type hints

logger = get_logger("email_dao")

# --- Contact Functions ---

def insert_contacts(contacts: List[Dict[str, Any]]):
    """
    Inserts or updates contacts in the database using MERGE.
    Expects a list of contact dictionaries (like those from HubSpot client).
    """
    if not contacts:
        logger.warning("No contacts provided to insert_contacts.")
        return

    # Removed unused variables: inserted_count, updated_count
    error_count = 0

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            for contact in contacts:
                contact_id = contact.get('id')
                properties = contact.get('properties', {})
                email = properties.get('email')
                firstname = properties.get('firstname', '')
                lastname = properties.get('lastname', '')

                if not contact_id or not email:
                    logger.warning(f"Skipping contact due to missing ID or Email: {contact}")
                    error_count += 1
                    continue

                try:
                    # Using MERGE requires specific syntax depending on the DB (e.g., SQL Server, Oracle)
                    # This example assumes SQL Server syntax. Adjust if using a different DB.
                    # Consider adding a 'last_updated_at' column.
                    cursor.execute("""
                        MERGE INTO contacts AS target
                        USING (SELECT ? AS id, ? AS firstname, ? AS lastname, ? AS email) AS source
                        ON target.id = source.id
                        WHEN MATCHED THEN
                            UPDATE SET
                                firstname = source.firstname,
                                lastname = source.lastname,
                                email = source.email -- Add last_updated_at = GETDATE() or similar
                        WHEN NOT MATCHED THEN
                            INSERT (id, firstname, lastname, email) -- Add created_at, last_updated_at
                            VALUES (source.id, source.firstname, source.lastname, source.email); -- Add GETDATE(), GETDATE()
                    """, contact_id, firstname, lastname, email)

                    # Check rows affected if the DB driver supports it reliably (can be tricky with MERGE)
                    # if cursor.rowcount > 0: # Example check
                    #    logger.debug(f"Merged contact {contact_id}")
                    # For simplicity, we won't track inserted vs updated precisely here without more complex logic

                except Exception as merge_err:
                    logger.error(f"Error merging contact {contact_id}: {merge_err}")
                    error_count += 1
                    # Optionally rollback transaction per contact or handle errors differently

            conn.commit()
            # Log summary - precise counts might require more logic
            # The log message correctly reflects the available information
            logger.info(f"Contact sync complete. Processed: {len(contacts)}, Errors: {error_count}.")

        except Exception as e:
            logger.error(f"Critical error during batch contact insert/update: {e}")
            conn.rollback() # Rollback the whole batch on critical error
        # No finally block needed for cursor close when using 'with get_db_connection()'

# ... (rest of the file remains the same) ...

def _fetch_all_contacts_sync() -> List[Tuple[str, str, str, str]]:
    """Synchronous helper to fetch all contacts."""
    logger.debug("Fetching all contacts from DB...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Assuming 'id' is VARCHAR to match HubSpot IDs
        cursor.execute("SELECT id, firstname, lastname, email FROM Contacts")
        results = cursor.fetchall()
        logger.debug(f"Fetched {len(results)} contacts.")
        return results

async def fetch_all_contacts() -> List[Tuple[str, str, str, str]]:
    """Asynchronously fetches all contacts from the database."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_all_contacts_sync)

def _fetch_emails_needing_validation_sync() -> List[Tuple[str, str, str, str]]:
    """Synchronous helper to fetch contacts needing email validation."""
    logger.debug("Fetching contacts needing validation from DB...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Adjust WHERE clause based on your actual validation tracking columns
        # This assumes a 'validation_results' table exists as per the save_validation_result below
        # Or modify the 'contacts' table to have validation status columns
        cursor.execute("""
            SELECT c.id, c.firstname, c.lastname, c.email
            FROM Contacts c
            LEFT JOIN validation_results vr ON c.id = vr.contact_id
            WHERE vr.contact_id IS NULL OR vr.email != c.email -- Validate if not validated or email changed
        """)
        # Alternative if validation status is on Contacts table:
        # cursor.execute("SELECT id, firstname, lastname, email FROM Contacts WHERE email_validation_status IS NULL OR email_validation_status = 'pending'")
        results = cursor.fetchall()
        logger.debug(f"Fetched {len(results)} contacts needing validation.")
        return results

async def fetch_emails_needing_validation() -> List[Tuple[str, str, str, str]]:
    """Asynchronously fetches contacts needing email validation."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_emails_needing_validation_sync)


# --- Validation Result Functions ---

def save_validation_result(validation_result: Dict[str, Any], contact_id: str):
    """
    Saves the detailed email validation result to the validation_results table.
    Uses MERGE to insert or update based on contact_id.
    """
    logger.debug(f"Saving validation result for contact {contact_id}")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Using MERGE to handle inserts or updates for validation results
            cursor.execute("""
                MERGE INTO validation_results AS target
                USING (SELECT
                    ? AS contact_id,
                    ? AS email,
                    ? AS domain,
                    ? AS mx_valid,
                    ? AS is_disposable,
                    ? AS is_blacklisted,
                    ? AS is_free_provider,
                    ? AS validation_status, -- Added status
                    ? AS validation_message -- Added message
                    -- Add a timestamp column like 'validated_at'
                ) AS source
                ON target.contact_id = source.contact_id
                WHEN MATCHED THEN
                    UPDATE SET
                        email = source.email,
                        domain = source.domain,
                        mx_valid = source.mx_valid,
                        is_disposable = source.is_disposable,
                        is_blacklisted = source.is_blacklisted,
                        is_free_provider = source.is_free_provider,
                        validation_status = source.validation_status,
                        validation_message = source.validation_message
                        -- validated_at = GETDATE() or similar
                WHEN NOT MATCHED THEN
                    INSERT (contact_id, email, domain, mx_valid, is_disposable, is_blacklisted, is_free_provider, validation_status, validation_message) -- Add validated_at
                    VALUES (source.contact_id, source.email, source.domain, source.mx_valid, source.is_disposable, source.is_blacklisted, source.is_free_provider, source.validation_status, source.validation_message); -- Add GETDATE()
            """,
            contact_id,
            validation_result.get('email', ''),
            validation_result.get('domain', ''),
            validation_result.get('mx_valid', False),
            validation_result.get('is_disposable', False),
            validation_result.get('is_blacklisted', False),
            validation_result.get('is_free_provider', False),
            validation_result.get('status', 'unknown'), # Save status
            validation_result.get('message', '') # Save message
            )

            conn.commit()
            logger.info(f"Validation result for contact {contact_id} saved/updated successfully.")
        except Exception as e:
            logger.error(f"Error saving validation result for contact {contact_id}: {e}")
            conn.rollback() # Rollback on error
        # No finally block needed for cursor close

# The function above handles saving the detailed results.

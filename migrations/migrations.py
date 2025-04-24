# migrations/migrations.py
# (Ensure print statements are present as shown in the previous response)
from db.connector import get_db_connection

def create_contacts_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Using INFORMATION_SCHEMA for better compatibility/standardization
        cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = SCHEMA_NAME()
            AND TABLE_NAME = 'contacts'
        )
        CREATE TABLE contacts (
            contact_id VARCHAR(100) PRIMARY KEY,
            firstname NVARCHAR(255),
            lastname NVARCHAR(255),
            email NVARCHAR(320), -- Match length with validation_results
            created_at DATETIME DEFAULT GETDATE() -- Added created_at back
        )
        """)
        conn.commit()
        print("Checked/Created 'contacts' table.") # <<< Ensure present

def create_validation_results_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = SCHEMA_NAME()
                AND TABLE_NAME = 'validation_results'
            )
            CREATE TABLE validation_results (
                id INT IDENTITY(1,1) PRIMARY KEY,
                contact_id VARCHAR(100), -- Should match contacts.id type/length
                email VARCHAR(320), -- Ensure consistency
                domain VARCHAR(253),
                mx_valid BIT,
                is_disposable BIT,
                is_blacklisted BIT,
                is_free_provider BIT,
                created_at DATETIME DEFAULT GETDATE()
                -- Optional: Add foreign key constraint
                -- CONSTRAINT FK_ValidationResults_Contacts FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("Checked/Created 'validation_results' table.") # <<< Ensure present


def run_migrations():
    """Runs all required database migrations."""
    print("Running database migrations...") # <<< Ensure present
    create_contacts_table()
    create_validation_results_table()
    print("Database migrations finished.") # <<< Ensure present

if __name__ == "__main__":
    run_migrations()

# migrations/migrations.py
from db.connector import get_db_connection

def create_contacts_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='contacts' AND xtype='U')
        CREATE TABLE contacts (
            id VARCHAR(100) PRIMARY KEY,
            firstname NVARCHAR(255),
            lastname NVARCHAR(255),
            email NVARCHAR(255)
        )
        """)
        conn.commit()

def create_validation_results_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = 'validation_results'
            )
            CREATE TABLE validation_results (
                id INT IDENTITY(1,1) PRIMARY KEY,
                contact_id VARCHAR(100),
                email VARCHAR(320),
                domain VARCHAR(253),
                mx_valid BIT,
                is_disposable BIT,
                is_blacklisted BIT,
                is_free_provider BIT,
                created_at DATETIME DEFAULT GETDATE()
            )
        """)
        conn.commit()

def run_migrations():
    create_contacts_table()
    create_validation_results_table()

if __name__ == "__main__":
    run_migrations()

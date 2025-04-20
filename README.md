# ️ SQL | 🟠 HubSpot | 🚀 FastAPI | 🐍 Python**

##  Custom Email API & HubSpot Contact Sync 🔄

This project provides tools to synchronize contacts from a HubSpot account into a local database and perform email validation on those contacts.

## ✨ Features

*   **🤝 HubSpot Contact Synchronization:** Fetches contact data (specifically email addresses) from your HubSpot account using the HubSpot API.
*   **💾 Database Storage:** Stores fetched contact information and email validation results in a SQL Server database.
*   **✅ Email Validation:** Includes schema definition for storing detailed email validation results (MX record validity, disposable domain check, blacklist status, free provider check). *(Note: The actual validation logic implementation is not shown in the provided context but the database schema supports it).*
*   **📝 Structured Logging:** Utilizes a logger for tracking application flow and debugging.

## 🛠️ Prerequisites

Before you begin, ensure you have met the following requirements:

*   **🐍 Python:** Version 3.8+ recommended.
*   **📦 Pip:** Python package installer.
*   **🐙 Git:** Version control system.
*   **🗄️ SQL Server:** A running instance of SQL Server.
*   **🟠 HubSpot Account:** Access to a HubSpot account with API key generation permissions (specifically for reading contacts).

## ⚙️ Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd custom-email-api
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    *(Assuming you have a `requirements.txt` file)*
    ```bash
    pip install -r requirements.txt
    ```
    *If you don't have a `requirements.txt` yet, you'll need to create one based on the imports in your Python files (e.g., `requests` for HubSpot client, `pyodbc` or similar for SQL Server, etc.).*

4.  **Database Setup:**
    *   Ensure your SQL Server instance is running.
    *   Create a database named `hubspot_contacts`.
    *   Connect to your SQL Server instance (using SSMS, Azure Data Studio, or `sqlcmd`) and run the `create_validation_table.sql` script to create the `validation_results` table within the `hubspot_contacts` database.
        ```sql
        -- Example using sqlcmd (replace placeholders)
        sqlcmd -S your_server_name -U your_username -P your_password -d hubspot_contacts -i create_validation_table.sql
        ```
    *   **Note:** The schema for the main contacts table (where contacts are initially inserted by `sync_contacts.py` via `db.email_dao.insert_contacts`) is not defined in the provided SQL. Ensure this table exists or is created by your `db` module setup.

## 🔑 Configuration

This application requires configuration for connecting to HubSpot and your database. It's recommended to use environment variables. Create a `.env` file in the project root:

```dotenv
# .env file
HUBSPOT_API_KEY=your_hubspot_api_key

# SQL Server Connection Details (adjust as needed for your db driver)
DB_DRIVER={ODBC Driver 17 for SQL Server} # Or your appropriate driver
DB_SERVER=your_server_name_or_ip
DB_NAME=hubspot_contacts
DB_USER=your_database_username
DB_PASSWORD=your_database_password
# Alternatively, provide a full connection string if your db module expects that:
# DATABASE_URL='mssql+pyodbc://your_username:your_password@your_server_name/hubspot_contacts?driver=ODBC+Driver+17+for+SQL+Server'

Ensure your Python code (e.g., in `hubspot_client` and `db` modules) is configured to read these environment variables (e.g., using `python-dotenv` and `os.getenv`).

## 🚀 Usage

### Syncing HubSpot Contacts

To fetch contacts from HubSpot and insert/update them in your database, run the synchronization script:

```bash
python sync_contacts.py

This script will:

Call the HubSpot API via hubspot_client.contacts_client.fetch_hubspot_contacts().
Pass the retrieved contacts to db.email_dao.insert_contacts() for database insertion.
Log activities using the configured logger.
Email Validation
The create_validation_table.sql script sets up the validation_results table to store validation outcomes. The actual process for performing the validation and populating this table would likely involve:

Retrieving contacts from the database (either newly synced or all contacts).
Using an email validation service or library (e.g., AbstractAPI, ZeroBounce, or custom checks) for each email.
Storing the results (validity status, MX check, disposable status, etc.) in the validation_results table, linking back to the contact via contact_id.
(The script/module responsible for performing the validation step is not included in the provided context but is a core intended function based on the database schema).

### Email Validation

The create_validation_table.sql script sets up the validation_results table to store validation outcomes. The actual process for performing the validation and populating this table would likely involve:

Retrieving contacts from the database (either newly synced or all contacts).
Using an email validation service or library (e.g., AbstractAPI, ZeroBounce, or custom checks) for each email.
Storing the results (validity status, MX check, disposable status, etc.) in the validation_results table, linking back to the contact via contact_id.
(The script/module responsible for performing the validation step is not included in the provided context but is a core intended function based on the database schema).

### 📁 Project Structure (Example)

```plaintext
custom-email-api/
├── .env                # 🔒 Local environment variables (DO NOT COMMIT if contains secrets)
├── .gitignore          # 🚫 Git ignore file
├── create_validation_table.sql # 📄 SQL script for validation results table
├── requirements.txt    # 📋 Python dependencies
├── sync_contacts.py    # ▶️ Main script for syncing contacts
│
├── db/                 # 🗄️ Database related modules
│   ├── __init__.py
│   └── email_dao.py    # 💾 Data Access Object for emails/contacts
│
├── hubspot_client/     # 🟠 HubSpot API interaction modules
│   ├── __init__.py
│   └── contacts_client.py # 👥 Client for fetching HubSpot contacts
│
├── utils/              # 🛠️ Utility modules
│   ├── __init__.py
│   └── logger.py       # 📝 Logging setup
│
└── venv/               # 🌱 Virtual environment directory (if used)

### 🤝 Contributing
Contributions are welcome! Please follow standard Git workflow (fork, branch, pull request). Ensure code is formatted, tested (if applicable), and follows the project's conventions.

### 📜 License
MIT

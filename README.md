# HubSend: Validate. Sync. Send Smarter from HubSpot

## ️ SQL Server | 🟠 HubSpot | 🚀 FastAPI | 🐍 Python

## Custom Email API & HubSpot Contact Sync 🔄

This project provides a FastAPI application to manage HubSpot contacts, store them in a local SQL Server database, perform detailed email validation, and sync validation results back to HubSpot.

## ✨ Features

* **🚀 FastAPI Backend:** Exposes API endpoints for validating emails, managing contacts, and triggering sync processes.
* **🤝 HubSpot Integration:**
  * Fetches contacts from HubSpot.
  * Creates and updates contacts in HubSpot.
  * Automatically creates and updates custom HubSpot properties with email validation results.
* **💾 Database Storage (SQL Server):**
  * Stores contact information (ID, name, email).
  * Stores detailed email validation results linked to contacts.
  * Uses `pyodbc` for connectivity and `MERGE` statements for efficient upserts.
  * Manages database schema via Python migration scripts (`migrations/migrations.py`).
* **✅ Comprehensive Email Validation:**
  * Orchestrates multiple asynchronous checks (`services/validation_orchestrator.py`).
  * Checks MX Records using `aiodns` (`validators/mx_checker.py`).
  * Identifies disposable email domains (`validators/disposable_checker.py`).
  * Checks against a domain blacklist (`validators/blacklist_checker.py`).
  * Identifies free email providers (`validators/free_provider_checker.py`).
* **🔄 Background Task Processing:** Uses FastAPI's `BackgroundTasks` for potentially long-running operations like validating all HubSpot contacts.
* **📝 Structured Logging:** Utilizes `utils/logger.py` for clear application monitoring and debugging.
* **🛡️ Robust Error Handling:** Includes specific exception handling for HubSpot API interactions (`hubspot_client/exceptions.py`).

## 🛠️ Prerequisites

Before you begin, ensure you have met the following requirements:

* **🐍 Python:** Version 3.8+ recommended (uses features like `asyncio`, `asynccontextmanager`).
* **📦 Pip:** Python package installer.
* **🐙 Git:** Version control system.
* **🗄️ SQL Server:** A running instance of SQL Server accessible via Windows Authentication from where the application runs.
* **🟠 HubSpot Account:** Access to a HubSpot account with API key generation permissions (for creating/reading contacts and managing custom properties).

## ⚙️ Setup & Installation (Running the Existing Project)

Follow these steps if you want to clone and run the project with its existing features.

1. **Clone the repository:**

    ```bash
    git clone <your-repository-url>
    cd custom-email-api
    ```

2. **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```

    * On Windows

    ```powershell
    .\venv\Scripts\activate
    ```

    * On macOS/Linux

    ```bash
    source venv/bin/activate
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Database Setup:**
    * Ensure your SQL Server instance is running and accessible via Windows Authentication.
    * Decide on a database name (e.g., `hubspot_email_validation`). You will configure this name in the `.env` file.
    * **Run the database migrations script** to create the necessary tables (`contacts` and `validation_results`):

        ```bash
        python -m migrations.migrations
        ```

    * This script connects using the settings defined in your `.env` file (see Configuration below) and creates the tables if they don't exist. The `create_validation_table.sql` file is for reference only.

## 🔑 Configuration

This application uses environment variables for configuration. Create a `.env` file in the project root with the following content:

```dotenv
# .env file - Local environment variables (DO NOT COMMIT)
```

### HubSpot Configuration

HUBSPOT_API_KEY=your_hubspot_api_key_here

### SQL Server Connection Details (using Windows Authentication)

DB_DRIVER={ODBC Driver 17 for SQL Server} # Verify/update if using a different driver
DB_SERVER=YOUR_SERVER_NAME[\INSTANCE_NAME] # e.g., localhost\SQLEXPRESS or your_server.database.windows.net
DB_DATABASE=hubspot_email_validation # The name of the database you want to use

### Optional: Logging Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### LOG_LEVEL=INFO

* Replace your_hubspot_api_key_here with your actual HubSpot private app token or API key.
* Replace YOUR_SERVER_NAME[\INSTANCE_NAME] with your SQL Server instance details.
* Replace hubspot_email_validation with your chosen database name if different.
* The application uses Windows Authentication (Trusted_Connection=yes in db/connector.py), so DB_USER and DB_PASSWORD variables are not needed. Ensure the user running the Python application has the necessary permissions on the SQL Server database.

## 🚀 Usage (Running the Existing Project)

### Running the API Server

To start the FastAPI application, use uvicorn:

```bash
uvicorn main:app --reload
```

* `main:app` tells uvicorn to find the app object inside the main.py file.
* `--reload` enables auto-reloading when code changes, useful for development.

The API will typically be available at `http://127.0.0.1:8000`. You can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

### API Endpoints

The following endpoints are available. Examples assume the API is running locally at `http://127.0.0.1:8000`. Replace this base URL if your API is hosted elsewhere. Replace placeholder values (like `test@example.com`, `12345`) with actual data.

* **`GET /`**
  * * **Description:** Root endpoint to check if the API is running.
  * * **Returns:** `{"message": "API is up and running!"}`
  * * **`curl` Example:**

        ```bash
        curl http://127.0.0.1:8000/
        ```

  * * **PowerShell Example:**

        ```powershell
        Invoke-RestMethod -Uri http://127.0.0.1:8000/
        ```

* **`GET /validate-email`**
  * * **Description:** Validates a single email address using all configured checks (MX, disposable, blacklist, free provider). Does *not* save to DB or update HubSpot.
* * * **Query Parameter:** `email` (string, required)
  * * **Returns:** A JSON object with detailed validation results.
  * * **`curl` Example:**

        ```bash
        # Replace test@example.com with the email to validate
        curl -G http://127.0.0.1:8000/validate-email --data-urlencode "email=test@example.com"
        # Or simply:
        # curl "http://127.0.0.1:8000/validate-email?email=test@example.com"
        ```

  * * **PowerShell Example:**

        ```powershell
        # Replace test@example.com with the email to validate
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/validate-email?email=test@example.com"
        ```

* **`POST /validate-hubspot-contacts`**
  * * **Description:** Fetches all contacts from HubSpot and schedules background tasks to validate each contact's email, save the results to the local DB, and update the contact's custom properties in HubSpot. This is an asynchronous operation.
  * * **Returns:** A confirmation message indicating how many validation tasks were scheduled.
  * * **Error Handling:** Returns appropriate HTTP errors (e.g., 429 Rate Limit, 503 Service Unavailable) if fetching contacts from HubSpot fails initially. Background task errors are logged.
  * * **`curl` Example:**

        ```bash
        curl -X POST http://127.0.0.1:8000/validate-hubspot-contacts
        ```

  * **PowerShell Example:**
        ```powershell
        Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/validate-hubspot-contacts
        ```

* **`PATCH /validate-email-and-update-hubspot/{contact_id}`**
  * * **Description:** Immediately validates a *specific email address* and updates the validation results for the *specified HubSpot contact ID* in both the local database and HubSpot.
  * * **Path Parameter:** `contact_id` (string, required) - The HubSpot ID of the contact to update.
  * * **Query Parameter:** `email` (string, required) - The email address to validate.
  * **Returns:** Success message with validation results upon successful validation and sync.
  * **Error Handling:** Returns HTTP errors if validation fails (400), orchestration fails (500), or DB/HubSpot sync fails (502 Bad Gateway).
  * **`curl` Example:**
        ```bash
        # Replace 12345 with the actual HubSpot Contact ID
        # Replace contact@domain.com with the email to validate for that contact
        curl -X PATCH "http://127.0.0.1:8000/validate-email-and-update-hubspot/12345?email=contact@domain.com"
        ```
  * **PowerShell Example:**
        ```powershell
        # Replace 123456789101 with the actual HubSpot Contact ID
        # Replace contact@domain.com with the email to validate for that contact
        Invoke-RestMethod -Method PATCH -Uri "http://127.0.0.1:8000/validate-email-and-update-hubspot/123456789101?email=contact@domain.com"
        ```

* **`POST /upsert-contact`**
  * * **Description:** Validates the provided email address first. If validation doesn't result in an 'error' status, it then creates a new contact in HubSpot or updates an existing one (based on email). The validation results are included in the data sent to HubSpot and also saved to the local database after a successful HubSpot upsert.
  * **Query Parameters:**
    * `email` (string, required)
    * `firstname` (string, optional)
    * `lastname` (string, optional)
  * **Returns:** The HubSpot API response for the create/update operation. May include a `db_save_warning` if saving validation results locally failed.
  * **Error Handling:** Returns 400 if initial email validation fails with status 'error'. Returns other HTTP errors for HubSpot API issues.
  * **`curl` Example:**
        ```bash
        # Replace email, firstname, and lastname with desired values
        curl -X POST "<http://127.0.0.1:8000/upsert-contact?email=new.lead@company.com&firstname=New&lastname=Lead>"
        # Example with only email:
        curl -X POST "http://127.0.0.1:8000/upsert-contact?email=another.lead@company.com"
        ```

  * **PowerShell Example:**
        ```powershell
        # Replace email, firstname, and lastname with desired values
        Invoke-RestMethod -Method POST -Uri "<http://127.0.0.1:8000/upsert-contact?email=new.lead@company.com&firstname=New&lastname=Lead>"
        # Example with only email:
        Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/upsert-contact?email=another.lead@company.com"
        ```

### ✅ Email Validation

This API performs several checks to validate email addresses and assess their quality. The validation logic is orchestrated asynchronously in `services/validation_orchestrator.py` and utilizes individual, specialized checkers found in the `validators/` directory.

**Checks Performed:**

The `services/validation_orchestrator.py` coordinates the following concurrent checks for a given email address:

1. **MX Record Check (`validators/mx_checker.py`):** Verifies the domain associated with the email has valid Mail Exchanger (MX) records by performing asynchronous DNS lookups using `aiodns`. This helps confirm the domain is configured to receive email. Invalid TLDs and common test domains are excluded.
2. **Disposable Domain Check (`validators/disposable_checker.py`):** Identifies if the email's domain belongs to a known temporary or disposable email service provider based on a predefined list (`DISPOSABLE_DOMAINS`).
3. **Blacklist Check (`validators/blacklist_checker.py`):** Checks if the email's domain is present on a predefined list of potentially problematic domains (`BLACKLISTED_DOMAINS`).
4. **Free Provider Check (`validators/free_provider_checker.py`):** Determines if the email address uses a common free email provider (like Gmail, Outlook, Yahoo) based on a predefined list (`FREE_EMAIL_PROVIDERS`). This can be useful context, especially in B2B scenarios.

**Integration and Data Flow:**

* **Orchestration:** The `perform_email_validation_checks` function in `services/validation_orchestrator.py` gathers results from all checkers. It determines an overall `status` (`valid`, `warning`, `error`) and provides a descriptive `message` based on the outcomes (e.g., prioritizing errors like invalid MX or disposable domains over warnings like free providers). The `validate_and_sync` function in the same module extends this by handling database saving and HubSpot updates.
* **Database Storage:** Validation results (including individual check outcomes, status, and message) are saved to the `validation_results` table in the SQL Server database.
  * The database connection is managed by `db/connector.py` (using `pyodbc` and Windows Authentication based on environment variables).
  * The table schema is defined in `migrations/migrations.py`.
  * The `db/email_dao.py` module's `save_validation_result` function handles the `MERGE` operation (run via `run_in_executor`) to insert or update these results, linked by `contact_id`.
* **HubSpot Sync:** For operations involving HubSpot contacts (like `/validate-hubspot-contacts`, `/validate-email-and-update-hubspot/{contact_id}`, `/upsert-contact`), the validation results are automatically synced to custom properties created on the HubSpot contact record (managed by `hubspot_client/contacts_client.py`). The `validate_and_sync` function in the orchestrator handles both DB saving and HubSpot updating (also via `run_in_executor`).
* **API Endpoints (`main.py`):**
  * `GET /validate-email`: Directly uses the orchestrator (`validate_and_sync` without `contact_id`) to validate an email without DB/HubSpot interaction.
  * `POST /validate-hubspot-contacts`: Fetches contacts and schedules background tasks using `validate_and_sync` for full validation, DB save, and HubSpot update.
  * `PATCH /validate-email-and-update-hubspot/{contact_id}`: Performs immediate validation, DB save, and HubSpot update for a specific contact using `validate_and_sync`.
  * `POST /upsert-contact`: Performs validation *first* using `perform_email_validation_checks`, then proceeds with HubSpot upsert and subsequent DB save (`db_save_validation_result`) if validation passes.

This integrated approach ensures that email validation is a core part of contact management within the API, providing data consistency across the local database and HubSpot.

### 📁 Project Structure

This diagram shows the core source code structure. Generated directories like `__pycache__` or the venv directory are omitted for clarity. The `scaffold.ps1` and `scaffold.sh` scripts are utilities for project generation and not part of the running application's structure.

```plaintext
custom-email-api/
├── .env                     # 🔒 Local environment variables (DO NOT COMMIT)
├── .gitignore               # 🚫 Git ignore file
├── create_validation_table.sql # 📄 [Optional] SQL script for reference (schema managed by migrations)
├── main.py                  # ▶️ FastAPI application entry point (API endpoints)
├── README.md                # 📖 This file
├── requirements.txt         # 📋 Python dependencies
├── scaffold.ps1             # 🏗️ [Utility] Project scaffolding script (PowerShell)
├── scaffold.sh              # 🏗️ [Utility] Project scaffolding script (Bash)
├── sync_contacts.py         # ▶️ Standalone script for bulk syncing contacts (if still used)
│
├── db/                      # 🗄️ Database interaction modules
│   ├── connector.py         # 🔗 Database connection setup (pyodbc)
│   ├── email_dao.py         # 💾 Data Access Object for contacts & validation results
│   └── __init__.py
│
├── hubspot_client/          # 🟠 HubSpot API interaction modules
│   ├── contacts_client.py   # 👥 Client for HubSpot contact operations (fetch, update, upsert)
│   ├── exceptions.py        # ❗ Custom HubSpot API exceptions
│   └── __init__.py
│
├── migrations/              # 🔄 Database schema migration scripts
│   └── migrations.py        # ✨ Defines and applies table creation/updates
│
├── services/                # ⚙️ Business logic and orchestration
│   ├── validation_orchestrator.py # 🚦 Coordinates email validation checks, DB save, HubSpot sync
│   └── __init__.py
│
├── utils/                   # 🛠️ Utility modules
│   ├── domain_utils.py      # 🌐 Helper for extracting email domains
│   ├── logger.py            # 📝 Logging setup
│   └── __init__.py
│
├── validators/              # ✅ Individual email validation checkers
│   ├── blacklist_checker.py # ⚫ Checks against domain blacklist
│   ├── disposable_checker.py# 🗑️ Checks for disposable email domains
│   ├── free_provider_checker.py # 🆓 Checks for free email providers (Gmail, etc.)
│   ├── mx_checker.py        # 📧 Checks for valid MX DNS records
│   └── __init__.py
│
└── venv/                    # 🌱 Virtual environment directory (Created by user, ignored by Git)
```

## Project Scaffolding (Optional - Starting a New Project)

Use these helper scripts if you want to generate the project's directory structure and placeholder files as a template for a new project, rather than cloning the existing application logic.

These scripts will:

* Create the necessary directories (db, services, validators, etc.).
* Create empty Python files (.py) including `__init__.py` files for packages.
* Create essential root files like `.gitignore`, `.env`, `main.py`, `requirements.txt`.
* Add standard, recommended entries to `.gitignore` and `.env if the files are empty.

**Note:** These scripts do not install dependencies or set up the virtual environment. They only create the file/folder structure. You will need to add your own application logic.

### Using PowerShell (Windows)

1. Save the PowerShell script, `scaffold.ps1`, in your desired project root directory.
2. Open PowerShell in that directory.
3. Run the script:

    ```powershell
    .\scaffold.ps1
    ```

   _(You might need to adjust your execution policy: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)*

### Using Bash (Linux/macOS)

1. Save the bash script, `scaffold.sh` in your desired project root directory.
2. Open the terminal in that directory.
3. Make the script executable:

    ```bash
    chmod +x scaffold.sh
    ```

4. Run the script:

    ```bash
    ./scaffold.sh
    ```

### 🤝 Contributing

Contributions are welcome! Please follow standard Git workflow (fork, branch, pull request). Ensure code is formatted, tested (if applicable), and follows the project's conventions.

### 📜 License

MIT

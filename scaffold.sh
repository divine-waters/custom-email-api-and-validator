#!/bin/bash
# scaffold.sh - Creates the basic project structure for custom-email-api

echo "Starting project scaffolding..."

# Define folders (excluding venv)
folders=("db" "hubspot_client" "migrations" "services" "utils" "validators")

# Define files within folders (associative array for easier handling)
declare -A files
files["db"]="__init__.py connector.py email_dao.py"
files["hubspot_client"]="__init__.py contacts_client.py exceptions.py"
files["migrations"]="__init__.py migrations.py" # Note: migrations.py is specific
files["services"]="__init__.py validation_orchestrator.py"
files["utils"]="__init__.py domain_utils.py logger.py"
files["validators"]="__init__.py blacklist_checker.py disposable_checker.py free_provider_checker.py mx_checker.py"

# Define top-level files (excluding venv related)
rootFiles=("main.py" "requirements.txt" "README.md" ".gitignore" ".env" "create_validation_table.sql" "sync_contacts.py")

# --- Script Execution ---

# Create folders
echo "Creating directories..."
for folder in "${folders[@]}"; do
    if [ ! -d "$folder" ]; then
        mkdir -p "$folder"
        echo "  [+] Created: $folder/"
    else
        echo "  [=] Exists:  $folder/"
    fi
done

# Create files within folders
echo "Creating files within directories..."
for folder in "${!files[@]}"; do # Iterate over keys (folder names)
    for file in ${files[$folder]}; do # Iterate over files in the current folder
        filePath="$folder/$file"
        if [ ! -f "$filePath" ]; then
            touch "$filePath"
            # Add simple placeholder if it's an __init__.py
            if [ "$file" == "__init__.py" ]; then
                echo "# $folder/__init__.py" > "$filePath"
            fi
            echo "  [+] Created: $filePath"
        else
            echo "  [=] Exists:  $filePath"
        fi
    done
done

# Create top-level files
echo "Creating root files..."
for file in "${rootFiles[@]}"; do
    if [ ! -f "$file" ]; then
        touch "$file"
        echo "  [+] Created: $file"
    else
        echo "  [=] Exists:  $file"
    fi
done

# Add refined content to .gitignore if it's empty or newly created
if [ ! -s ".gitignore" ]; then # Check if file exists and has size greater than zero
    echo "Adding basic content to .gitignore..."
    cat << EOF > .gitignore
# Virtual environment
venv/

# Environment variables
.env
.env.*

# Python cache
__pycache__/
*.pyc

# Logs
*.log
logs/

# OS generated files
.DS_Store
Thumbs.db
EOF
else
    echo ".gitignore already has content, skipping default additions."
fi

# Add basic content to .env if it's empty or newly created
if [ ! -s ".env" ]; then # Check if file exists and has size greater than zero
    echo "Adding basic content to .env..."
    cat << EOF > .env
# .env file - Local environment variables (DO NOT COMMIT)

# HubSpot Configuration
HUBSPOT_API_KEY=your_hubspot_api_key_here

# SQL Server Connection Details (using Windows Authentication)
DB_DRIVER={ODBC Driver 17 for SQL Server} # Verify/update if using a different driver
DB_SERVER=YOUR_SERVER_NAME[\\INSTANCE_NAME] # e.g., localhost\\SQLEXPRESS or your_server.database.windows.net
DB_DATABASE=hubspot_email_validation # The name of the database you want to use

# Optional: Logging Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
# LOG_LEVEL=INFO
EOF
else
    echo ".env already has content, skipping default additions."
fi

echo "Scaffolding complete."

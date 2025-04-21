# scaffold.ps1 - Creates the basic project structure for custom-email-api

# Define folders (excluding venv)
$folders = @("db", "hubspot_client", "migrations", "services", "utils", "validators")

# Define files within folders (including __init__.py)
$files = @{
    "db"             = @("__init__.py", "connector.py", "email_dao.py")
    "hubspot_client" = @("__init__.py", "contacts_client.py", "exceptions.py")
    "migrations"     = @("__init__.py", "migrations.py") # migrations.py is specific
    "services"       = @("__init__.py", "validation_orchestrator.py")
    "utils"          = @("__init__.py", "domain_utils.py", "logger.py")
    "validators"     = @("__init__.py", "blacklist_checker.py", "disposable_checker.py", "free_provider_checker.py", "mx_checker.py")
}

# Define top-level files (excluding venv related)
$rootFiles = @("main.py", "requirements.txt", "README.md", ".gitignore", ".env", "create_validation_table.sql", "sync_contacts.py")

# --- Script Execution ---

Write-Host "Starting project scaffolding..." -ForegroundColor Yellow

# Get the directory where the script is located
$scriptRoot = $PSScriptRoot

# Create folders
Write-Host "Creating directories..." -ForegroundColor Cyan
$folders | ForEach-Object {
    $folderPath = Join-Path -Path $scriptRoot -ChildPath $_
    if (-not (Test-Path $folderPath -PathType Container)) {
        New-Item -ItemType Directory -Path $folderPath -Force | Out-Null
        Write-Host "  [+] Created: $_/"
    } else {
        Write-Host "  [=] Exists:  $_/"
    }
}

# Create files within folders
Write-Host "Creating files within directories..." -ForegroundColor Cyan
$files.Keys | ForEach-Object {
    $folder = $_
    $folderPath = Join-Path -Path $scriptRoot -ChildPath $folder
    $files[$folder] | ForEach-Object {
        $fileName = $_
        $filePath = Join-Path -Path $folderPath -ChildPath $fileName
        if (-not (Test-Path $filePath -PathType Leaf)) {
            New-Item -ItemType File -Path $filePath -Force | Out-Null
            # Add simple placeholder if it's an __init__.py
            if ($fileName -eq "__init__.py") {
                "# $folder/__init__.py" | Out-File -FilePath $filePath -Encoding utf8
            }
             Write-Host "  [+] Created: $folder/$fileName"
        } else {
            Write-Host "  [=] Exists:  $folder/$fileName"
        }
    }
}

# Create top-level files
Write-Host "Creating root files..." -ForegroundColor Cyan
$rootFiles | ForEach-Object {
    $fileName = $_
    $filePath = Join-Path -Path $scriptRoot -ChildPath $fileName
    if (-not (Test-Path $filePath -PathType Leaf)) {
        New-Item -ItemType File -Path $filePath -Force | Out-Null
         Write-Host "  [+] Created: $fileName"
    } else {
         Write-Host "  [=] Exists:  $fileName"
    }
}

# Add refined content to .gitignore if it's empty or newly created
$gitignorePath = Join-Path -Path $scriptRoot -ChildPath ".gitignore"
if ((Get-Item $gitignorePath).Length -eq 0) {
    Write-Host "Adding basic content to .gitignore..." -ForegroundColor Cyan
    @(
        "# Virtual environment",
        "venv/",
        "",
        "# Environment variables",
        ".env",
        ".env.*",
        "",
        "# Python cache",
        "__pycache__/",
        "*.pyc",
        "",
        "# Logs",
        "*.log",
        "logs/",
        "",
        "# OS generated files",
        ".DS_Store",
        "Thumbs.db"
    ) | Out-File -FilePath $gitignorePath -Encoding utf8
} else {
     Write-Host ".gitignore already has content, skipping default additions." -ForegroundColor Gray
}


# Add basic content to .env if it's empty or newly created
$envPath = Join-Path -Path $scriptRoot -ChildPath ".env"
if ((Get-Item $envPath).Length -eq 0) {
    Write-Host "Adding basic content to .env..." -ForegroundColor Cyan
    @(
        "# .env file - Local environment variables (DO NOT COMMIT)",
        "",
        "# HubSpot Configuration",
        "HUBSPOT_API_KEY=your_hubspot_api_key_here",
        "",
        "# SQL Server Connection Details (using Windows Authentication)",
        "DB_DRIVER={ODBC Driver 17 for SQL Server} # Verify/update if using a different driver",
        "DB_SERVER=YOUR_SERVER_NAME[\\INSTANCE_NAME] # e.g., localhost\\SQLEXPRESS or your_server.database.windows.net",
        "DB_DATABASE=hubspot_email_validation # The name of the database you want to use",
        "",
        "# Optional: Logging Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        "# LOG_LEVEL=INFO"
    ) | Out-File -FilePath $envPath -Encoding utf8
} else {
     Write-Host ".env already has content, skipping default additions." -ForegroundColor Gray
}


Write-Host "Scaffolding complete." -ForegroundColor Green

$folders = @("validators", "api", "utils", "data")
$files = @{
    "validators" = @("mx_check.py", "disposable_check.py", "blacklist_check.py", "free_provider_check.py")
    "api"        = @("app.py")
    "utils"      = @("domain_utils.py")
    "data"       = @("disposable_domains.txt", "blacklisted_domains.txt", "free_providers.txt")
}

# Create folders
$folders | ForEach-Object { New-Item -ItemType Directory -Path $_ -Force }

# Create files
$files.Keys | ForEach-Object {
    $folder = $_
    $files[$folder] | ForEach-Object {
        New-Item -ItemType File -Path "$folder/$_" -Force
    }
}

New-Item -ItemType File -Path "requirements.txt" -Force

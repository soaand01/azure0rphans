# Development Mode

## Overview
CostPlan supports a development mode that separates dev and production scan files and prevents accidental deletion of scans during development.

## Features

### In Development Mode:
- Scan files are saved with `azure_environment_dev_` prefix
- Only dev scan files are visible in the UI
- Delete buttons are hidden and delete operations are blocked (returns 403 error)
- UI shows "(Development Mode)" label in scan management

### In Production Mode:
- Scan files are saved with `azure_environment_` prefix (without `dev_`)
- Only production scan files are visible in the UI
- Delete operations are allowed

## Enabling Development Mode

### Method 1: Environment Variable
```bash
export DEV_MODE=true
python app.py
```

### Method 2: Inline with Command
```bash
DEV_MODE=true python app.py
```

### Method 3: Using FLASK_ENV
```bash
export FLASK_ENV=development
python app.py
```

## Checking Current Mode

The mode is displayed in the scan management modal:
- "X scans • Y MB total (Development Mode)" - Dev mode active
- "X scans • Y MB total" - Production mode

## File Naming

- **Dev files**: `azure_environment_dev_20251216_134616.json`
- **Production files**: `azure_environment_20251216_134616.json`

## Use Cases

- **Development**: Test scanning and analysis without affecting production scan history
- **Production**: Manage actual production scans with ability to clean up old files
- **Separation**: Keep dev and prod scans completely isolated

## Safety Features

- Dev mode blocks all delete operations at the API level (403 Forbidden)
- UI automatically hides delete buttons in dev mode
- File filtering ensures dev/prod scans never mix in the UI

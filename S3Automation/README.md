# S3 Automation for Game Data Backups

This system automatically processes hourly game data backups from an S3 bucket and pushes the parsed CSV reports to the roarealmdata repository.

## Architecture

- **S3 Bucket**: `rise-of-atlantis-csv-exports` (OVH Cloud S3 in eu-west-par)
- **Processing**: Uses local `player_data_analyzer.py` to parse tar.gz backups
- **Deployment**: GitHub Actions workflow running hourly
- **Output**: Comprehensive CSV files pushed to roarealmdata repository

## Setup Instructions

### 1. GitHub Repository Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `S3_ACCESS_KEY_ID`: Your S3 access key
- `S3_SECRET_ACCESS_KEY`: Your S3 secret key
- `PAT_TOKEN`: GitHub Personal Access Token with repo scope (for pushing to roarealmdata)

### 2. GitHub Actions Workflow

The workflow is located in `.github/workflows/s3-automation.yml`. It:
- Runs every hour via cron schedule
- Can be manually triggered via workflow_dispatch
- Downloads the most recent tar.gz file from S3
- Processes it using player_data_analyzer.py
- Pushes the resulting CSV to roarealmdata repository

### 3. Target Repository

The automation pushes CSV files to the `roarealmdata` repository. Ensure:
- You have write access to this repository
- The repository exists and is accessible

## How It Works

1. **S3 Connection**: Connects to OVH Cloud S3 using provided credentials
2. **File Monitoring**: Lists all files in the bucket and identifies the most recent tar.gz backup
3. **Download**: Downloads the tar.gz file to a temporary directory
4. **Processing**: Uses `PlayerDataAnalyzer` to:
   - Extract the tar.gz file
   - Process all CSV files (player.csv, item.csv, troop.csv, etc.)
   - Generate comprehensive_player_data CSV
5. **GitHub Push**: Pushes the parsed CSV file to roarealmdata repository via GitHub API

## File Naming Convention

Output files follow the pattern: `comprehensive_player_data_YYYY-MM-DD_HHMMSS.csv.gz`

Example: `comprehensive_player_data_2026-04-11_020500.csv.gz`

## Manual Testing

To test the automation locally:

```bash
cd S3Automation
pip install -r requirements.txt

# Set environment variables
export S3_ACCESS_KEY_ID="your_key"
export S3_SECRET_ACCESS_KEY="your_secret"
export PAT_TOKEN="your_github_token"
export GITHUB_OWNER="your_github_username"
export GITHUB_REPO="roarealmdata"

# Run the automation
python s3_automation.py
```

## Troubleshooting

### S3 Connection Issues
- Verify S3 credentials are correct
- Check that the bucket name and region are correct
- Ensure network access to OVH Cloud S3

### GitHub Push Issues
- Verify GitHub token has repo scope
- Check that you have write access to roarealmdata
- Ensure the repository exists

### Processing Errors
- Check that the tar.gz file format matches expected structure
- Verify that player_data_analyzer.py is accessible
- Review logs for specific error messages

## Dependencies

- boto3: S3 SDK for Python
- requests: HTTP library for GitHub API
- Standard library: tarfile, tempfile, shutil, datetime, pathlib

## Customization

To change the schedule:
- Edit the cron expression in `.github/workflows/s3-automation.yml`

To process multiple files per run:
- Modify the `run()` method in `s3_automation.py` to process more than just the most recent file

To change the target repository:
- Update the `GITHUB_REPO` environment variable in the workflow

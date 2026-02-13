#!/bin/bash

# Dental AI Grant Finder - Daily Cron Job
# Add this to your crontab to run daily at 9 AM:
# 0 9 * * * /path/to/dental-ai-grant-finder/ops/cron_example.sh

# Set the project directory
PROJECT_DIR="/path/to/dental-ai-grant-finder"

# Change to project directory
cd "$PROJECT_DIR" || {
    echo "Failed to change to project directory: $PROJECT_DIR"
    exit 1
}

# Activate virtual environment (if using one)
# source venv/bin/activate

# Run the pipeline
echo "$(date): Starting Dental AI Grant Finder pipeline" >> logs/cron.log
python -m src.pipeline >> logs/cron.log 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "$(date): Pipeline completed successfully" >> logs/cron.log
else
    echo "$(date): Pipeline failed with exit code $?" >> logs/cron.log
    # Optionally send alert email
    # echo "Dental AI Grant Finder pipeline failed" | mail -s "Pipeline Failure" your-email@example.com
fi 
#!/bin/zsh

# Navigate to your project directory
cd /Users/alishali/Desktop/alishali.info

# Ensure the latest changes from GitHub are pulled (optional, prevents conflicts)
git pull origin main

# Add the updated Anki data file
git add anki_data.json

# Commit the changes with a timestamp
git commit -m "Auto-update Anki data: $(date)"

# Push to GitHub
git push origin main
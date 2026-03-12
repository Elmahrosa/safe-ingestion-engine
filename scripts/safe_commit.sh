#!/bin/bash
set -e

# Pull latest changes with rebase to avoid merge commits
git pull --rebase origin main

# Stage all changes
git add .

# Commit with the message you pass as argument
git commit -m "$1"

# Push to remote
git push origin main

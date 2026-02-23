#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

BACKUP_DIR=".backup"
REMOTE="git@github.com:aaryan-dharmadhikari/paper-mind-data.git"

# Init backup repo once
if [ ! -d "$BACKUP_DIR/.git" ]; then
    mkdir -p "$BACKUP_DIR"
    git -C "$BACKUP_DIR" init
    git -C "$BACKUP_DIR" remote add origin "$REMOTE" 2>/dev/null || true
    git -C "$BACKUP_DIR" branch -m main
fi

# Copy data in
cp -r uploads "$BACKUP_DIR/" 2>/dev/null || true
cp -r data "$BACKUP_DIR/" 2>/dev/null || true

# Commit and push if there are changes
cd "$BACKUP_DIR"
git add -A
if git diff --cached --quiet; then
    echo "No changes to back up"
else
    git commit -m "backup $(date +%Y-%m-%d_%H:%M)"
    git push -u origin main
fi

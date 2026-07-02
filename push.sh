#!/bin/bash
# Run from anywhere — pushes latest index.html to GitHub Pages
cd "$(dirname "$0")"

# Clear any stale lock files left by the sandbox
rm -f .git/HEAD.lock .git/index.lock .git/MERGE_HEAD.lock
rm -f .git/refs/remotes/origin/main.lock

git add -A
git commit -m "Update STR Analyzer - $(date '+%Y-%m-%d')"
git push
echo ""
echo "Live at https://str.alexcomery.com/ in ~60s"

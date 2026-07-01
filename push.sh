#!/bin/bash
# Run this from the str-analyzer folder after Claude regenerates index.html
cd "$(dirname "$0")"
git add index.html
git commit -m "Update STR Analyzer - $(date '+%Y-%m-%d')"
git push
echo ""
echo "Deployed! Live in ~60 seconds at https://yukoncamino.github.io/str-analyzer/"

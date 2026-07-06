#!/usr/bin/env bash
# Sync site/ to enaguthi.com (Abhishek21g.github.io gh-pages branch).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${SITE_REPO:-$HOME/Documents/Abhishek21g.github.io}"

if [[ ! -d "$DEST/.git" ]]; then
  echo "error: main site repo not found at $DEST" >&2
  echo "Clone it: git clone git@github.com:Abhishek21g/Abhishek21g.github.io.git $DEST" >&2
  exit 1
fi

echo "Syncing $ROOT/site/ -> $DEST/tinker-workbench/site/"
rsync -av --delete "$ROOT/site/" "$DEST/tinker-workbench/site/"
cp "$ROOT/index.html" "$DEST/tinker-workbench/index.html"

cd "$DEST"
git checkout gh-pages
git add tinker-workbench/
if git diff --cached --quiet; then
  echo "No site changes to publish."
  exit 0
fi

git commit -m "Sync Tinker Workbench dashboard from tinker-workbench"
git pull --rebase origin gh-pages
git push origin gh-pages

echo "Published: https://enaguthi.com/tinker-workbench/site/"

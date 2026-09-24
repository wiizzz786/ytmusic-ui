#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================="
echo " Creating & Pushing YT Music UI to new GitHub Repo..."
echo "========================================================="

# Create repo and push via gh CLI
"$DIR/gh" repo create ytmusic-ui --public --source=. --remote=origin --push

echo "========================================================="
echo " Successfully pushed to GitHub!"
echo " Repository URL: https://github.com/wiizzz786/ytmusic-ui"
echo "========================================================="

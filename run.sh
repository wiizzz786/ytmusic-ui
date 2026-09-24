#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================="
echo " Starting YouTube Music UI Server..."
echo " Opening http://127.0.0.1:5000 in your browser..."
echo " Or open: $DIR/index.html directly!"
echo "========================================================="

# Open browser after 1.5s delay
(sleep 1.5 && open "http://127.0.0.1:5000/index.html") &

# Start python app using venv
"$DIR/venv/bin/python" "$DIR/app.py"

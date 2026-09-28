#!/usr/bin/env bash
# Double-click on a Mac (or run in a terminal on Linux). If macOS blocks it:
# right-click -> Open, or in Terminal type  bash  then drag install.sh in and press Enter.
cd "$(dirname "$0")" && exec bash ./install.sh "$@"

#!/usr/bin/env bash
# run.sh - start Live Subtitles with the project's virtual environment.
# Any options are passed through, e.g.  ./run.sh --model small --font-size 32
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Not installed yet. Run ./install.sh first."; exit 1
fi
exec .venv/bin/python live_subtitles.py "$@"

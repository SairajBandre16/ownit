#!/bin/sh
# Start LanguageTool in the background, wait until it answers, then serve the API.
set -e

LT_DIR=$(find "$OWNIT_DATA_DIR/languagetool" -maxdepth 1 -type d -name 'LanguageTool-*' | head -n 1)
if [ -n "$LT_DIR" ]; then
  (cd "$LT_DIR" && java -Xms256m -Xmx${LT_HEAP:-1g} -cp languagetool-server.jar \
      org.languagetool.server.HTTPServer --port 8010 --allow-origin '*' >/tmp/languagetool.log 2>&1) &
  for _ in $(seq 1 60); do
    if curl -sf "http://127.0.0.1:8010/v2/languages" >/dev/null; then
      echo "LanguageTool is up"
      break
    fi
    sleep 1
  done
else
  echo "LanguageTool not found; grammar checks will be off" >&2
  export OWNIT_LANGUAGETOOL=0
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}" --workers "${WORKERS:-1}"

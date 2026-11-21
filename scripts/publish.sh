#!/data/user/0/com.termux/files/usr/bin/bash
# Roz news fetch karein, pages banayein aur (agar repo set ho) GitHub par push karein.
# Cron isi script ko chalata hai. Log: logs/publish.log
set -uo pipefail

SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SITE_DIR" || exit 1
[[ -f "$SITE_DIR/config.sh" ]] && source "$SITE_DIR/config.sh"
mkdir -p logs

echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') =====" >> logs/publish.log

# SITE_URL apne Vercel domain ke hisaab se set karein (README dekhen).
export SITE_URL="${SITE_URL:-https://example.vercel.app}"
export SITE_NAME="${SITE_NAME:-खबर 24}"

if ! python3 scripts/fetch_news.py >> logs/publish.log 2>&1; then
  echo "FETCH FAILED — purane pages safe hain." >> logs/publish.log
  exit 1
fi

# GitHub push tabhi jab remote configured ho aur AUTO_PUSH=1 ho.
if [[ "${AUTO_PUSH:-0}" == "1" ]] && git remote get-url origin >/dev/null 2>&1; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "News update $(date '+%Y-%m-%d %H:%M')" >> logs/publish.log 2>&1
    if git push origin HEAD >> logs/publish.log 2>&1; then
      echo "PUSH OK — Vercel auto-deploy chalega." >> logs/publish.log
    else
      echo "PUSH FAILED — check git credentials/token." >> logs/publish.log
    fi
  else
    echo "Koi nayi khabar nahi, push skip." >> logs/publish.log
  fi
fi

echo "" >> logs/publish.log

#!/data/user/0/com.termux/files/usr/bin/bash
# GitHub repo + auto-push setup. Token sirf is phone par save hota hai, chat me nahi jata.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=== GitHub setup ==="
read -rp "GitHub username: " USERNAME
read -rp "Repo name (e.g. hindi-news): " REPO
read -rsp "Personal Access Token (likhte waqt nahi dikhega): " TOKEN
echo ""
read -rp "Vercel URL (abhi nahi hai to bas Enter dabayein): " SITE_URL
SITE_URL="${SITE_URL:-https://example.vercel.app}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -q
fi

git config user.email "${USERNAME}@users.noreply.github.com"
git config user.name "News Bot"
git branch -M main

git remote remove origin 2>/dev/null || true
git remote add origin "https://${USERNAME}:${TOKEN}@github.com/${USERNAME}/${REPO}.git"

cat > config.sh <<EOF
# Local settings — is file ko GitHub par push nahi kiya jata
export SITE_URL="${SITE_URL}"
export SITE_NAME="खबर 24"
export AUTO_PUSH=1
EOF
chmod 600 config.sh

git add -A || true
git commit -qm "Setup GitHub auto-push" || true

echo ""
echo "GitHub par push kar rahe hain..."
git push -u origin main

echo ""
echo "✅ Ho gaya! Ab Vercel par jakar ye repo import karein:"
echo "   https://vercel.com/new"
echo "Deploy milne par Vercel URL config.sh me SITE_URL badal dena,"
echo "ya phir mujhe URL bata do — main update kar dunga."

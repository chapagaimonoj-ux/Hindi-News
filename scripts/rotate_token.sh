#!/data/user/0/com.termux/files/usr/bin/bash
# Purana token revoke karne ke baad naya token yahan chhupa kar daalein.
# Token sirf local .git/config me jata hai, kahin bhi save nahi hota.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

USERNAME="${GITHUB_USER:-chapagaimonoj-ux}"
REPO="${GITHUB_REPO:-Hindi-News}"

read -rsp "Naya GitHub token (chhupa hua): " TOKEN
echo ""
if [[ -z "$TOKEN" ]]; then
  echo "Token khali hai!" >&2
  exit 1
fi

git remote set-url origin "https://${USERNAME}:${TOKEN}@github.com/${USERNAME}/${REPO}.git"
echo "Remote URL update ho gaya. Ab test push kar rahe hain..."
git push origin main
echo "✅ Naya token chal gaya. Purana token ab GitHub par revoke kar sakte ho."

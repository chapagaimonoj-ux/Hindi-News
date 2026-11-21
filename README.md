# खबर 24 — Hindi News Website (auto update)

**🔴 LIVE:** https://chapagaimonoj-ux.github.io/Hindi-News/

GitHub Pages पर host है — Vercel की zarurat nahi.

एक completamente free, statically-generated हिंदी न्यूज़ साइट जो Google News (Hindi) RSS से खबरें लाती है और रोज़ अपने आप नए पेज बनाती है।

## क्या-क्या है

| फ़ाइल | काम |
|------|-----|
| `index.html` | होमपेज (स्क्रिप्ट खुद बनाती है) |
| `news/*.html` | हर खबर का अलग SEO page |
| `news.json` | सारी खबरों का डेटा |
| `sitemap.xml`, `robots.txt` | Google indexing |
| `scripts/fetch_news.py` | RSS → HTML generator (सिर्फ Python stdlib) |
| `scripts/publish.sh` | fetch + git commit + push (cron इसी को चलाता है) |
| `assets/style.css`, `assets/app.js` | डिज़ाइन और फ़िल्टर |

## 1️⃣ Local test (अभी चल रहा है)

```bash
cd ~/projects/hindi-news-site
python3 scripts/fetch_news.py
# index.html को ब्राउज़र में खोलें
```

## 2️⃣ Free deploy (Vercel)

1. GitHub पर जाकर एक नया **public repo** बनाएँ (नाम जैसे `hindi-news`).
2. Termux में:

```bash
cd ~/projects/hindi-news-site
git init
git add .
git commit -m "Initial news site"
git branch -M main
git remote add origin https://github.com/<USERNAME>/<REPO>.git
git push -u origin main
```

3. https://vercel.com पर GitHub से login करें → **Add New → Project** → repo import → **Deploy**.
4. मिले URL को `scripts/publish.sh` और अपने environment में डालें:

```bash
export SITE_URL="https://your-project.vercel.app"
export AUTO_PUSH=1
```

> Git push के लिए Personal Access Token (PAT) चाहिए, क्योंकि Termux में interactive login नहीं hota. Token GitHub → Settings → Developer settings → Personal access tokens से बनाएँ, फिर remote URL ऐसी रखें:
> `https://<USERNAME>:<TOKEN>@github.com/<USERNAME>/<REPO>.git`

हर push पर Vercel अपने आप नया deploy kar deta hai.

## 3️⃣ Termux cron (रोज़ auto-update)

```bash
pkg install cronie
crond                      # daemon start (रोज़ चलाने के लिए termux-wake-lock भी लगाएँ)
crontab -e
```

ये लाइन डालें (सुबह 7, दोपहर 1, शाम 7 — तीन बार):

```
0 7,13,19 * * * cd /data/user/0/com.termux/files/home/projects/hindi-news-site && ./scripts/publish.sh >> logs/cron.log 2>&1
```

नोट: Android battery optimization के कारण cron tabband ho sakta hai. Termux को **Don't optimize / battery exemption** देना ज़रूरी है और चाहें तो `termux-wake-lock` command इस्तेमाल करें। (24/7 guaranteed चाहिए तो GitHub Actions best है — बताओ तो वो भी बना दूँगा।)

लॉग देखने के लिए: `tail -f logs/publish.log`

## 4️⃣ AdSense / earning

1. साइट को कम से कम 2-4 हफ्ते चलाएँ, ~20-30 quality pages होने दें, **About/Contact/Privacy Policy** pages जोड़ें — फिर Google AdSense के लिए apply करें.
2. Approval मिलने पर AdSense dashboard से ad code लें और **`ads.html`** में दिए गए markers (`TOP`, `FEED`, `SIDEBAR`, `ARTICLE`) के नीचे paste करें। Generator इसे सभी pages में अपने आप inject कर देगा — रोज़ regeneration से आपका ad code **नहीं** मिटेगा। बस `python3 scripts/fetch_news.py` दोबारा चलाएँ।
3. स्रोत का credit और लिंक हमेशा रखें — copy-paste वाली सामग्री AdSense reject करता है।

## 5️⃣ Custom domain (बाद में)

Vercel → Project → Settings → Domains → अपना `.com`/`.in` domain जोड़ें। फिर `SITE_URL` नए domain पर set करें ताकि sitemap सही बने।

## ⚠️ ईमानदार सलाह

- AdSense से पैसा तब आता है जब **traffic** हो। रोज़ खबर डालना शुरुआत है; SEO + WhatsApp/Telegram/social पर sharing भी ज़रूरी है।
- गूगल न्यूज़ की headlines सार्वजनिक RSS से आती हैं; हम सारांश + मूल लिंक देते हैं (पूरा article copy नहीं करते) — ये सुरक्षित तरीका है।
- अगर全自动 cloud automation चाहिए (फोन बंद रहे तो भी), वो GitHub Actions से free में बना सकता हूँ।

## 🔧 Quick commands

```bash
python3 scripts/fetch_news.py     # अभी खबरें अपडेट करें
./scripts/publish.sh              # fetch + push
tail -f logs/publish.log          # लॉग
crontab -l                        # cron देखें
```

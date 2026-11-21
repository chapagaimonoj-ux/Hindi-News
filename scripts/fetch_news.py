#!/usr/bin/env python3
"""
Hindi news site generator.
Google News (Hindi) RSS feeds se khabre laakar static HTML pages banata hai:
  - index.html          (homepage)
  - news/<slug>.html    (har khabar ka apna page)
  - news.json           (raw data)
  - sitemap.xml, robots.txt

Sirf Python standard library use hota hai - koi pip package nahi chahiye.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    import xml.etree.ElementTree as ET
    ET.fromstring(b"<x/>")  # Termux par kabhi-kabhi expat missing hota hai
except Exception:
    ET = None

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))
SITE_NAME = os.environ.get("SITE_NAME", "खबर 24")
SITE_URL = os.environ.get("SITE_URL", "https://example.vercel.app").rstrip("/")
MAX_AGE_HOURS = 72
PER_CATEGORY = 6
MAX_POSTS = 40

QUERIES = {
    "देश": "भारत when:2d",
    "दुनिया": "विश्व समाचार when:2d",
    "राजनीति": "राजनीति when:2d",
    "खेल": "क्रिकेट OR खेल when:2d",
    "मनोरंजन": "बॉलीवुड OR फिल्म when:2d",
    "व्यापार": "शेयर बाजार OR अर्थव्यवस्था when:2d",
    "टेक्नोलॉजी": "मोबाइल OR आर्टिफिशियल इंटेलिजेंस when:2d",
}
CATEGORIES = list(QUERIES)

UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"


def log(msg: str) -> None:
    print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] {msg}", flush=True)


def feed_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=hi&gl=IN&ceid=IN:hi"
    )


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, */*"})
    with urlopen(req, timeout=25) as resp:
        return resp.read()


def clean_text(value: str) -> str:
    # Google RSS description double-escaped hota hai: &lt;a href...&gt;
    # pehle unescape, phir tags hatana zaroori hai.
    value = html.unescape(value or "")
    for _ in range(2):
        stripped = re.sub(r"<[^>]+>", " ", value)
        unescaped = html.unescape(stripped)
        if unescaped == value:
            break
        value = unescaped
    return re.sub(r"\s+", " ", value).strip()


def make_summary(title: str, description: str, source: str) -> str:
    desc = clean_text(description)
    # Google कभी-कभी अंत में अंग्रेज़ी अनुवाद जोड़ देता है: "... - english text..."
    desc = re.split(r"\s+-\s+[a-zA-Z][a-zA-Z\s,.;:']{25,}", desc)[0].strip()
    if len(desc) > len(title) + 25 and not desc.lower().startswith(title[:22].lower()):
        return desc[:230].rsplit(" ", 1)[0] + "…"
    return (
        f"{title} — यह खबर {source} द्वारा दी गई जानकारी पर आधारित है। "
        "पूरा समाचार मूल स्रोत पर जाएँ।"
    )


def get_image(item: ET.Element) -> str:
    for ns in ("http://search.yahoo.com/mrss/",):
        for tag in ("content", "thumbnail"):
            for el in item.findall(f"{{{ns}}}{tag}"):
                url = el.get("url", "")
                if url.startswith("http") and "gstatic.com" not in url:
                    return url
    return ""


def parse_feed_items(data: bytes) -> list[dict]:
    """ET (expat) हो तो वो, वरना pure-regex fallback — Termux friendly."""
    text = data.decode("utf-8", errors="replace")
    if ET is not None:
        root = ET.fromstring(data)
        result = []
        for node in root.findall(".//item"):
            src = node.find("source")
            result.append(
                {
                    "title": node.findtext("title", ""),
                    "link": node.findtext("link", ""),
                    "description": node.findtext("description", ""),
                    "pubDate": node.findtext("pubDate", ""),
                    "source": (src.text if src is not None else "") or "",
                    "image": get_image(node),
                }
            )
        return result

    result = []
    for block in re.findall(r"<item\b[^>]*>(.*?)</item>", text, re.S | re.I):
        def field(tag: str) -> str:
            m = re.search(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", block, re.S | re.I)
            value = m.group(1) if m else ""
            return re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", value.strip(), flags=re.S)

        def attr(tag: str, name: str = "url") -> str:
            m = re.search(rf"<{tag}\b[^>]*\b{name}=[\"']([^\"']+)", block, re.I)
            return m.group(1) if m else ""

        image = attr("media:content") or attr("media:thumbnail")
        result.append(
            {
                "title": field("title"),
                "link": field("link"),
                "description": field("description"),
                "pubDate": field("pubDate"),
                "source": field("source"),
                "image": image if "gstatic.com" not in image else "",
            }
        )
    return result


def parse_date(value: str) -> datetime:
    try:
        return parsedate_to_datetime(value).astimezone(IST)
    except Exception:
        return datetime.now(IST)


def human_time(dt: datetime) -> str:
    delta = datetime.now(IST) - dt
    if delta < timedelta(minutes=60):
        return f"{max(1, int(delta.total_seconds() // 60))} मिनट पहले"
    if delta < timedelta(hours=24):
        return f"{int(delta.total_seconds() // 3600)} घंटे पहले"
    return dt.strftime("%d %b %Y")


def slug_for(title: str) -> str:
    return "k" + hashlib.md5(title.encode("utf-8")).hexdigest()[:10]


def collect() -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    cutoff = datetime.now(IST) - timedelta(hours=MAX_AGE_HOURS)

    for category, query in QUERIES.items():
        try:
            feed_items = parse_feed_items(fetch(feed_url(query)))
        except Exception as exc:
            log(f"⚠ {category} feed fail: {exc}")
            continue

        count = 0
        for node in feed_items:
            title = clean_text(node["title"])
            # Google News अक्सर अंत में " -Times of India" लगा देता है
            title = re.sub(r"\s+[-–—]\s+[^\-–—]{2,40}$", "", title).strip()
            link = node["link"].strip()
            if not title or not link or count >= PER_CATEGORY:
                continue

            published = parse_date(node["pubDate"])
            if published < cutoff:
                continue

            source = clean_text(node["source"])
            if not source:
                source = "Google समाचार"

            key = re.sub(r"[^\w\u0900-\u097f]+", "", title.lower())
            if not key or key in seen:
                continue
            seen.add(key)
            count += 1

            items.append(
                {
                    "title": title,
                    "link": link,
                    "category": category,
                    "source": source,
                    "published": published.isoformat(),
                    "time_label": human_time(published),
                    "image": node["image"],
                    "summary": make_summary(title, node["description"], source),
                    "slug": slug_for(title),
                }
            )
        log(f"✓ {category}: {count} खबरें")

    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_POSTS]


# ---------------------------------------------------------------- HTML templates

STYLE = ""  # CSS assets/style.css में रखा गया है

PAGE_HEAD = """<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#c62828">
<title>{{TITLE}} | {{SITE_NAME}}</title>
<meta name="description" content="{{META_DESC}}">
<link rel="canonical" href="{{CANONICAL}}">
<meta property="og:type" content="website">
<meta property="og:title" content="{{TITLE}} | {{SITE_NAME}}">
<meta property="og:description" content="{{META_DESC}}">
<meta property="og:url" content="{{CANONICAL}}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{BASE}}assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{{BASE}}index.html"><span class="brand-mark">ख</span><span>{{SITE_NAME}}</span></a>
    <nav class="nav" id="nav">
      <a href="{{BASE}}index.html">मुख्य पृष्ठ</a>
      {{NAV_LINKS}}
    </nav>
    <button class="menu-btn" id="menuBtn" aria-label="मेन्यू">☰</button>
  </div>
</header>
"""

FOOTER = """
<footer class="site-footer">
  <div class="wrap footer-inner">
    <div>
      <div class="brand footer-brand"><span class="brand-mark">ख</span><span>{{SITE_NAME}}</span></div>
      <p class="footer-note">हिंदी समाचार एक जगह। समाचार Google News RSS के माध्यम से एकत्रित किए जाते हैं और मूल स्रोत से जोड़े जाते हैं।</p>
    </div>
    <div class="footer-links">
      <a href="{{BASE}}index.html">मुख्य पृष्ठ</a>
      <a href="{{SITE_URL}}/sitemap.xml">साइटमैप</a>
      <a href="#top">ऊपर जाएँ ↑</a>
    </div>
  </div>
  <div class="wrap copyright">© {{YEAR}} {{SITE_NAME}}। सभी समाचार सामग्री संबंधित समाचार संस्थाओं की संपत्ति है।</div>
</footer>
<script src="{{BASE}}assets/app.js"></script>
</body>
</html>
"""


def load_ads() -> dict:
    """ads.html में रखा ad code पढ़ें ताकि regeneration से न मिटे।"""
    sections = {"TOP": "", "FEED": "", "SIDEBAR": "", "ARTICLE": ""}
    ad_file = ROOT / "ads.html"
    if ad_file.exists():
        parts = re.split(r"<!--\s*(TOP|FEED|SIDEBAR|ARTICLE)\s*-->", ad_file.read_text(encoding="utf-8"))
        for i in range(1, len(parts) - 1, 2):
            sections[parts[i]] = parts[i + 1].strip()
    return sections


def inject_ads(page: str, ads: dict) -> str:
    for key, code in ads.items():
        if code:
            page = re.sub(rf"<!-- ADSENSE_{key}:.*?-->", code, page, flags=re.S)
    return page


def nav_links() -> str:
    return "".join(
        f'<a href="index.html#{cat}">{cat}</a>' for cat in CATEGORIES[:5]
    )


def base_context(base: str, title: str, meta_desc: str, canonical: str) -> dict:
    return {
        "{{BASE}}": base,
        "{{SITE_NAME}}": html.escape(SITE_NAME),
        "{{SITE_URL}}": SITE_URL,
        "{{YEAR}}": str(datetime.now(IST).year),
        "{{TITLE}}": html.escape(title),
        "{{META_DESC}}": html.escape(meta_desc),
        "{{CANONICAL}}": html.escape(canonical),
        "{{NAV_LINKS}}": nav_links(),
    }


def apply(template: str, context: dict) -> str:
    for key, value in context.items():
        template = template.replace(key, str(value))
    return template


def card_html(item: dict, base: str = "") -> str:
    img = (
        f'<img src="{html.escape(item["image"])}" alt="" loading="lazy" '
        'onerror="this.style.display=\'none\'">'
        if item["image"]
        else '<div class="no-image">ख</div>'
    )
    return f"""<article class="card" data-category="{html.escape(item['category'])}">
  <a class="card-image" href="{base}news/{item['slug']}.html">{img}<span class="badge">{html.escape(item['category'])}</span></a>
  <div class="card-body">
    <div class="meta"><span>{html.escape(item['source'])}</span><span class="dot">•</span><span>{html.escape(item['time_label'])}</span></div>
    <h3><a href="{base}news/{item['slug']}.html">{html.escape(item['title'])}</a></h3>
    <p>{html.escape(item['summary'][:150])}</p>
    <a class="read-more" href="{base}news/{item['slug']}.html">पढ़ें →</a>
  </div>
</article>"""


def build_home(items: list[dict], ads: dict | None = None) -> str:
    ctx = base_context("", "ताज़ा हिंदी समाचार", "आज की ताज़ा हिंदी खबरें — देश, दुनिया, राजनीति, खेल, मनोरंजन और व्यापार।", SITE_URL + "/")
    hero = items[0]
    hero_img = (
        f'<img src="{html.escape(hero["image"])}" alt="" onerror="this.style.display=\'none\'">'
        if hero["image"]
        else '<div class="no-image">ख</div>'
    )
    hero_html = f"""<section class="hero" id="top">
  <a class="hero-image" href="news/{hero['slug']}.html">{hero_img}</a>
  <div class="hero-content">
    <span class="badge badge-lg">ताज़ा खबर • {html.escape(hero['category'])}</span>
    <h1><a href="news/{hero['slug']}.html">{html.escape(hero['title'])}</a></h1>
    <p>{html.escape(hero['summary'][:230])}</p>
    <div class="meta"><span>{html.escape(hero['source'])}</span><span class="dot">•</span><span>{html.escape(hero['time_label'])}</span></div>
    <a class="btn" href="news/{hero['slug']}.html">पूरी खबर पढ़ें →</a>
  </div>
</section>"""

    cards = "\n".join(card_html(i) for i in items[1:])
    trending = "\n".join(
        f'<li><span>{n}</span><a href="news/{i["slug"]}.html">{html.escape(i["title"][:90])}</a></li>'
        for n, i in enumerate(items[:6], 1)
    )
    tabs = '<button class="tab active" data-filter="सभी">सभी</button>' + "".join(
        f'<button class="tab" data-filter="{html.escape(c)}">{html.escape(c)}</button>'
        for c in CATEGORIES
    )
    updated = datetime.now(IST).strftime("%d %b %Y, %I:%M %p")

    body = f"""
<div class="wrap">
  <div class="ticker"><span class="ticker-label">BREAKING</span><div class="ticker-scroll"><span>{html.escape(items[0]['title'])}</span><span class="dot">•</span><span>{html.escape(items[1]['title']) if len(items) > 1 else ''}</span></div></div>
  <div class="section-head"><h2>आज की खबरें</h2><span class="updated">अपडेट: {updated}</span></div>
  <!-- ADSENSE_TOP: अपना AdSense <script> कोड यहाँ paste करें -->
  {hero_html}
  <div class="main-grid">
    <div>
      <div class="tabs" id="tabs">{tabs}</div>
      <div class="card-grid" id="cardGrid">
{cards}
      </div>
      <!-- ADSENSE_FEED: दूसरा ad_unit यहाँ paste करें -->
    </div>
    <aside class="sidebar">
      <div class="side-box">
        <h3>🔴 ट्रेंडिंग</h3>
        <ol class="trending">{trending}</ol>
      </div>
      <div class="side-box about-box">
        <h3>हमारे बारे में</h3>
        <p>{html.escape(SITE_NAME)} — रोज़ ताज़ा हिंदी समाचार, एक सरल और तेज़ वेबसाइट पर। सभी खबरें मूल समाचार स्रोतों से जुड़ी हैं।</p>
      </div>
      <!-- ADSENSE_SIDEBAR: साइडबार ad_unit यहाँ paste करें -->
    </aside>
  </div>
</div>
{FOOTER}"""
    return inject_ads(apply(PAGE_HEAD + body, ctx), ads or load_ads())


def build_post(item: dict, items: list[dict], ads: dict | None = None) -> str:
    base = "../"
    canonical = f"{SITE_URL}/news/{item['slug']}.html"
    ctx = base_context(base, item["title"], item["summary"][:160], canonical)
    related = [i for i in items if i["slug"] != item["slug"]][:3]
    related_html = "\n".join(card_html(i, base) for i in related)
    img = (
        f'<img src="{html.escape(item["image"])}" alt="{html.escape(item["title"])}" onerror="this.parentElement.style.display=\'none\'">'
        if item["image"]
        else ""
    )
    body = f"""
<div class="wrap article-wrap" id="top">
  <div class="breadcrumb"><a href="{base}index.html">मुख्य पृष्ठ</a> › <span>{html.escape(item['category'])}</span></div>
  <article class="article">
    <span class="badge badge-lg">{html.escape(item['category'])}</span>
    <h1>{html.escape(item['title'])}</h1>
    <div class="article-meta"><span>📰 {html.escape(item['source'])}</span><span>🕒 {html.escape(item['time_label'])}</span></div>
    <figure class="article-image">{img}</figure>
    <p class="article-summary">{html.escape(item['summary'])}</p>
    <!-- ADSENSE_ARTICLE: लेख के अंदर ad_unit यहाँ paste करें -->
    <div class="source-box">
      <h3>पूरा समाचार कहाँ पढ़ें?</h3>
      <p>यह खबर <strong>{html.escape(item['source'])}</strong> द्वारा प्रकाशित की गई है। मूल, विस्तृत जानकारी समाचार स्रोत की वेबसाइट पर उपलब्ध है।</p>
      <a class="btn" href="{html.escape(item['link'])}" target="_blank" rel="noopener">मूल समाचार पढ़ें ↗</a>
    </div>
    <p class="disclaimer">नोट: हम केवल समाचार सूचना और लिंक साझा करते हैं; सभी सामग्री के अधिकार मूल समाचार संस्था के पास सुरक्षित हैं।</p>
  </article>
  <div class="section-head"><h2>और खबरें</h2><a href="{base}index.html">सभी खबरें →</a></div>
  <div class="card-grid related-grid">
{related_html}
  </div>
</div>
{FOOTER}"""
    return inject_ads(apply(PAGE_HEAD + body, ctx), ads or load_ads())


def build_sitemap(items: list[dict]) -> str:
    urls = [f"{SITE_URL}/", *(f"{SITE_URL}/news/{i['slug']}.html" for i in items)]
    body = "\n".join(
        f"  <url><loc>{html.escape(u)}</loc><lastmod>{datetime.now(IST).date()}</lastmod></url>"
        for u in urls
    )
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n"


def write_outputs(items: list[dict]) -> None:
    (ROOT / "news").mkdir(parents=True, exist_ok=True)
    ads = load_ads()
    (ROOT / "index.html").write_text(build_home(items, ads), encoding="utf-8")
    for item in items:
        (ROOT / "news" / f"{item['slug']}.html").write_text(
            build_post(item, items, ads), encoding="utf-8"
        )
    (ROOT / "news.json").write_text(
        json.dumps(
            {
                "site_name": SITE_NAME,
                "generated_at": datetime.now(IST).isoformat(),
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (ROOT / "sitemap.xml").write_text(build_sitemap(items), encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )


def main() -> int:
    log("RSS feeds se khabre la rahe hain…")
    items = collect()
    if not items:
        log("❌ Koi khabar nahi mili; purane pages waise hi chhod rahe hain.")
        return 1
    write_outputs(items)
    log(f"✅ Ho gaya: {len(items)} khabre, {len(items)} article pages likhe gaye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

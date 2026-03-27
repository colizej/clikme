#!/usr/bin/env python3
"""
Parity check: сравнивает URL оригинального clikme.ru с текущим Django-сайтом.

Использование:
    # Проверить оригинальный сайт (фиксируем baseline):
    python parity_check.py --mode live --save baseline.json

    # Проверить локальный Django после импорта:
    python parity_check.py --mode local --port 8003

    # Сравнить две сессии (до vs после):
    python parity_check.py --compare baseline.json new_check.json

Что проверяет:
    - HTTP статус каждого URL (200 / 301 / 404)
    - <title> страницы совпадает с ожидаемым из SQL
    - Наличие мета-описания
    - Отсутствие «Error» / Django debug traceback в теле
"""
import argparse
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# SSL context для проверки сайта (сертификат может быть самоподписным)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ── SQL Parser ────────────────────────────────────────────────────────────────

SQL_PATH = Path(__file__).parent / "opencart" / "u2971222_ocar341.sql"

# Marketplace-doc IDs: noindex после миграции
NOINDEX_IDS = {18, 22, 23, 24, 25, 32}

# IDs которые в категории 101 (pages app, не блог)
PAGES_CAT_IDS = {3, 4, 6, 7}


def parse_sql():
    """Парсит SQL-дамп, возвращает список статей blogs."""
    data = SQL_PATH.read_text(encoding="utf-8", errors="replace")

    # --- oc9a_information (id, image, status, views, date_added) ---
    info_rows = {}
    m = re.search(
        r"INSERT INTO `oc9a_information` VALUES (.*?);", data, re.DOTALL
    )
    if m:
        for row in re.findall(
            r"\((\d+),'([^']*)',\d+,\d+,\d+,(\d+),(\d+),'([^']*)'.*?'([^']*)'.*?'([^']*)'.*?'([^']*)'\)",
            m.group(1),
        ):
            oc_id, image, status, viewed, date_avail, date_end, date_added, date_mod = row
            info_rows[int(oc_id)] = {
                "image": image,
                "status": int(status),
                "viewed": int(viewed),
                "date_added": date_added,
                "date_modified": date_mod,
            }

    # --- oc9a_information_description (title, short_desc, content, meta) ---
    desc_rows = {}
    m = re.search(
        r"INSERT INTO `oc9a_information_description` VALUES (.*?);", data, re.DOTALL
    )
    if m:
        # Use a careful parser to handle nested quotes in HTML
        raw = m.group(1)
        # Split by language_id=1 rows only
        for match in re.finditer(
            r"\((\d+),1,'((?:[^'\\]|\\.|'')*?)','((?:[^'\\]|\\.|'')*?)','((?:[^'\\]|\\.|'')*?)',"
            r"'((?:[^'\\]|\\.|'')*?)','((?:[^'\\]|\\.|'')*?)','((?:[^'\\]|\\.|'')*?)','((?:[^'\\]|\\.|'')*?)','((?:[^'\\]|\\.|'')*?)'\)",
            raw,
        ):
            oc_id = int(match.group(1))
            desc_rows[oc_id] = {
                "title": _unescape(match.group(2)),
                "header": _unescape(match.group(3)),
                "short_description": _unescape(match.group(4)),
                "content": _unescape(match.group(5)),
                "tag": match.group(6),
                "meta_title": _unescape(match.group(7)),
                "meta_description": _unescape(match.group(8)),
                "meta_keyword": _unescape(match.group(9)),
            }

    # --- oc9a_seo_url (information_id → slug) ---
    slug_map = {}
    m = re.search(
        r"INSERT INTO `oc9a_seo_url` VALUES (.*?);", data, re.DOTALL
    )
    if m:
        for row in re.findall(
            r"\(\d+,\d+,\d+,'information_id=(\d+)','([^']*)'\)", m.group(1)
        ):
            oc_id, slug = int(row[0]), row[1]
            slug_map[oc_id] = slug

    # --- oc9a_information_to_category ---
    cat_map = {}  # info_id → set of category_ids
    m = re.search(
        r"INSERT INTO `oc9a_information_to_category` VALUES (.*?);", data, re.DOTALL
    )
    if m:
        for row in re.findall(r"\((\d+),(\d+),\d+\)", m.group(1)):
            info_id, cat_id = int(row[0]), int(row[1])
            cat_map.setdefault(info_id, set()).add(cat_id)

    # --- Compose articles list ---
    articles = []
    for oc_id, info in info_rows.items():
        cats = cat_map.get(oc_id, set())
        # Only blog articles (cat 90), skip pages (cat 101) and uncategorised
        if 90 not in cats:
            continue
        slug = slug_map.get(oc_id)
        if not slug:
            continue
        desc = desc_rows.get(oc_id, {})
        articles.append(
            {
                "oc_id": oc_id,
                "slug": slug,
                "title": desc.get("title", ""),
                "meta_title": desc.get("meta_title", "") or desc.get("title", ""),
                "status": info["status"],
                "noindex": oc_id in NOINDEX_IDS,
                "url": f"/{slug}/",
            }
        )

    articles.sort(key=lambda a: a["oc_id"])
    return articles


def _unescape(s: str) -> str:
    """Decode HTML entities и SQL escape sequences."""
    import html
    s = s.replace("\\'", "'").replace("\\\\", "\\").replace("\\n", "\n")
    return html.unescape(s)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ""
        self.meta_desc = ""

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attrs_d = dict(attrs)
            if attrs_d.get("name", "").lower() == "description":
                self.meta_desc = attrs_d.get("content", "")

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def fetch(url: str, timeout: int = 10) -> dict:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "clikme-parity-check/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            body = resp.read(32768).decode("utf-8", errors="replace")
            parser = TitleParser()
            parser.feed(body)
            has_error = (
                "Django" in body[:2000] and "Traceback" in body[:2000]
            ) or "Server Error" in body[:500]
            return {
                "status": resp.status,
                "final_url": resp.url,
                "title": parser.title.strip(),
                "meta_desc": bool(parser.meta_desc),
                "has_error": has_error,
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "final_url": url, "title": "", "meta_desc": False, "has_error": False}
    except Exception as e:
        return {"status": 0, "final_url": url, "title": "", "meta_desc": False, "has_error": False, "err": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def run_check(base_url: str, articles: list, delay: float = 0.3) -> list:
    results = []
    total = len(articles)
    for i, art in enumerate(articles, 1):
        # Percent-encode non-ASCII chars in the path (e.g., Cyrillic slugs)
        encoded_path = urllib.parse.quote(art["url"], safe="/")
        url = base_url.rstrip("/") + encoded_path
        result = fetch(url)
        entry = {
            "oc_id": art["oc_id"],
            "slug": art["slug"],
            "expected_title": art["meta_title"],
            "noindex": art["noindex"],
            "url": url,
            **result,
        }
        status_icon = {200: "✅", 301: "↪️ ", 302: "↪️ ", 404: "❌", 0: "💥"}.get(
            result["status"], f"[{result['status']}]"
        )
        title_ok = art["meta_title"].lower() in result.get("title", "").lower() if art["meta_title"] else True
        title_icon = "✅" if title_ok else "⚠️ "
        print(
            f"[{i:3}/{total}] {status_icon} {result['status']} {title_icon}"
            f"  /{art['slug'][:50]}"
        )
        results.append(entry)
        if delay:
            time.sleep(delay)
    return results


def print_summary(results: list):
    ok = sum(1 for r in results if r["status"] == 200)
    redir = sum(1 for r in results if r["status"] in (301, 302))
    not_found = sum(1 for r in results if r["status"] == 404)
    errors = sum(1 for r in results if r["status"] == 0)
    errors_body = sum(1 for r in results if r.get("has_error"))
    no_meta = sum(1 for r in results if not r["meta_desc"])

    print("\n" + "=" * 60)
    print(f"ИТОГО: {len(results)} URL")
    print(f"  ✅ 200 OK:       {ok}")
    print(f"  ↪️  301/302:     {redir}")
    print(f"  ❌ 404:          {not_found}")
    print(f"  💥 Ошибка сети: {errors}")
    print(f"  🐛 Django error: {errors_body}")
    print(f"  📵 Нет meta-desc: {no_meta}")
    print("=" * 60)

    if not_found:
        print("\n❌ 404 URLs:")
        for r in results:
            if r["status"] == 404:
                print(f"   {r['url']}")

    broken_title = [r for r in results if r["status"] == 200 and r["expected_title"]
                    and r["expected_title"].lower() not in r["title"].lower()]
    if broken_title:
        print(f"\n⚠️  Title mismatch ({len(broken_title)}):")
        for r in broken_title[:10]:
            print(f"   /{r['slug']}/")
            print(f"     ожидали: {r['expected_title']}")
            print(f"     получили: {r['title']}")


def compare_reports(path_a: str, path_b: str):
    a = {r["slug"]: r for r in json.loads(Path(path_a).read_text())}
    b = {r["slug"]: r for r in json.loads(Path(path_b).read_text())}
    all_slugs = set(a) | set(b)
    print(f"\nСравнение: {path_a} vs {path_b}")
    for slug in sorted(all_slugs):
        sa = a.get(slug, {}).get("status", "—")
        sb = b.get(slug, {}).get("status", "—")
        if sa != sb:
            icon = "📈" if sb == 200 else "📉"
            print(f"  {icon} /{slug}/  {sa} → {sb}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="clikme.ru parity check")
    parser.add_argument(
        "--mode",
        choices=["live", "local"],
        default="live",
        help="live = clikme.ru, local = localhost",
    )
    parser.add_argument("--port", type=int, default=8003, help="Порт локального сервера")
    parser.add_argument("--save", metavar="FILE", help="Сохранить результаты в JSON")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), help="Сравнить два JSON-файла")
    parser.add_argument("--delay", type=float, default=0.3, help="Задержка между запросами (сек)")
    args = parser.parse_args()

    if args.compare:
        compare_reports(*args.compare)
        return

    articles = parse_sql()
    print(f"Найдено {len(articles)} статей в SQL (категория 90)")

    if args.mode == "live":
        base_url = "https://clikme.ru"
        print(f"▶ Проверяем {base_url} (delay={args.delay}s)\n")
    else:
        base_url = f"http://127.0.0.1:{args.port}"
        print(f"▶ Проверяем локальный сервер {base_url}\n")

    results = run_check(base_url, articles, delay=args.delay)
    print_summary(results)

    if args.save:
        Path(args.save).write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"\n💾 Сохранено → {args.save}")


if __name__ == "__main__":
    main()

# Выгрузка постов канала alexcars10 с публичной страницы t.me/s (без входа).
import json, re, sys, time, html, urllib.request
CH = "alexcars10"
UA = {"User-Agent": "Mozilla/5.0"}
def get(url):
    for i in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            print("retry", url, e, flush=True); time.sleep(5 * (i + 1))
    raise SystemExit("fail " + url)
def text_of(block):
    m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
    if not m: return ""
    t = re.sub(r"<br\s*/?>", "\n", m.group(1))
    return html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
def page(before=None, ch=CH):
    """Одна страница канала: самые новые посты или посты с номером меньше before."""
    out = []
    for b in get("https://t.me/s/" + ch + (f"?before={before}" if before else "")).split('class="tgme_widget_message_wrap')[1:]:
        m = re.search(r'data-post="' + ch + r'/(\d+)"', b)
        if not m: continue
        dt = re.search(r'datetime="([^"]+)"', b)
        photos = re.findall(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", b)
        videos = len(re.findall(r"tgme_widget_message_video_player", b))
        out.append({"id": int(m.group(1)), "date": dt.group(1) if dt else None, "text": text_of(b), "photos": photos, "videos": videos})
    return out
def all_posts(ch=CH):
    """Весь канал, от новых к старым."""
    seen, before, res = set(), None, []
    while True:
        ps = page(before, ch)
        if not ps: break
        for p in ps:
            if p["id"] not in seen: seen.add(p["id"]); res.append(p)
        nb = min(p["id"] for p in ps)
        if before is not None and nb >= before: break
        before = nb
        print(f"page before={before} posts={len(res)}", flush=True)
        time.sleep(1.5)
    return res
if __name__ == "__main__":
    ps = all_posts(sys.argv[2] if len(sys.argv) > 2 else CH)
    with open(sys.argv[1], "w") as f:
        for p in ps: f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print("DONE posts", len(ps), flush=True)

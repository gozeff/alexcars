# Подгрузка канала для GitHub: обновляет data/posts.jsonl.
#   new  - 30 последних постов канала: новые и исправленные посты;
#   full - весь канал заново: удалённые в канале посты пропадают и с сайта.
# Печатает changed=1, если посты изменились (для GitHub Actions пишет то же в GITHUB_OUTPUT).
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrape
ROOT = os.environ.get("ALEX_ROOT", os.path.expanduser("~/alexcars")); P = ROOT + "/data/posts.jsonl"
mode = sys.argv[1] if len(sys.argv) > 1 else "new"
old = {p["id"]: p for p in map(json.loads, open(P))}
# ссылки на фото в сравнение не входят: важны текст, дата, число фото и видео
key = lambda p: (p["date"], p["text"], len(p["photos"]), p["videos"])
if mode == "full":
    got = scrape.all_posts()
    if len(got) < 0.9 * len(old) or min(p["id"] for p in got) > min(old) + 50:
        raise SystemExit(f"канал прочитан не целиком: {len(got)} постов против {len(old)} - ничего не меняю")
    new = {p["id"]: p for p in got}
else:
    new = dict(old)
    for p in scrape.all_posts(limit=30):
        new[p["id"]] = p
changed = set(new) != set(old) or any(key(new[i]) != key(old[i]) for i in new)
if changed:
    with open(P, "w") as f:
        for i in sorted(new, reverse=True): f.write(json.dumps(new[i], ensure_ascii=False) + "\n")
gone, added = len(set(old) - set(new)), len(set(new) - set(old))
print(f"{mode}: постов {len(new)}, новых {added}, удалено {gone}, changed={int(changed)}")
if os.environ.get("GITHUB_OUTPUT"):
    open(os.environ["GITHUB_OUTPUT"], "a").write(f"changed={int(changed)}\n")

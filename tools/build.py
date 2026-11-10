# Сборка сайта: data/cars.json + data/posts.jsonl + data/photos -> site/
import json, os, re, shutil, subprocess, sys, datetime, html, time, urllib.request
ROOT = os.environ.get("ALEX_ROOT", os.path.expanduser("~/alexcars")); D = ROOT + "/data"; S = ROOT + "/site"
cars = json.load(open(D + "/cars.json"))
posts = {json.loads(l)["id"]: json.loads(l) for l in open(D + "/posts.jsonl")}
thumbs_v = json.load(open(D + "/video_thumbs.json")) if os.path.exists(D + "/video_thumbs.json") else {}
# фото, которого нет на диске, скачивается по ссылке из поста (на GitHub оригиналов нет, есть только готовые webp)
URLS = {f"{D}/photos/{pid}_{i:02d}.jpg": u for pid, p in posts.items() for i, u in enumerate(p["photos"], 1)}
def fetch(url, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    for i in range(4):  # Telegram иногда отвечает ошибкой 500 - повторяем
        try:
            urllib.request.urlretrieve(url, dst); return True
        except Exception as e:
            err = e; time.sleep(3 * (i + 1))
    print("нет фото", url[:80], err); return False
def vthumb(pid):
    """Обложка видео со страницы поста; результат запоминается в video_thumbs.json, чтобы не спрашивать повторно."""
    if str(pid) not in thumbs_v:
        try:
            h = urllib.request.urlopen(urllib.request.Request(f"https://t.me/{json.load(open(ROOT + '/config.json'))['channel']}/{pid}?embed=1", headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode("utf-8", "replace")
            m = re.search(r"tgme_widget_message_video_thumb[^>]*url\('([^']+)'\)", h)
            thumbs_v[str(pid)] = int(bool(m) and fetch(m.group(1), f"{D}/vthumbs/{pid}.jpg"))
        except Exception as e:
            print("нет обложки видео", pid, e); return None
        json.dump(thumbs_v, open(D + "/video_thumbs.json", "w"))
    return thumbs_v[str(pid)]
car_ids = {c["id"] for c in cars}
os.makedirs(S + "/p", exist_ok=True); os.makedirs(S + "/t", exist_ok=True)

def webp(src, dst, w, q):
    if os.path.exists(dst) and os.path.getsize(dst) > 0: return True
    if (not os.path.exists(src) or os.path.getsize(src) == 0) and not (src in URLS and fetch(URLS[src], src)): return False
    r = subprocess.run(["cwebp", "-quiet", "-q", str(q), "-resize", str(w), "0", src, "-o", dst])
    return r.returncode == 0

# фото машин
for c in cars:
    ok = []
    for i in range(1, c["photos"] + 1):
        n = f"{c['id']}_{i:02d}"
        if webp(f"{D}/photos/{n}.jpg", f"{S}/p/{n}.webp", 800, 62): ok.append(i)
    c["ph"] = ok
    if ok: webp(f"{D}/photos/{c['id']}_{ok[0]:02d}.jpg", f"{S}/t/{c['id']}.webp", 420, 58)
    c["text"] = posts[c["id"]]["text"]
cars = [c for c in cars if c["ph"]]
# повторный пост того же автомобиля: в каталоге остаётся последний
rk = lambda c: (c["name"], c["km"], c["year"], c.get("month"), c.get("hp")) if c.get("km") and c.get("year") else ("id", c["id"])
last = {}
for c in cars:
    if rk(c) not in last or c["id"] > last[rk(c)]: last[rk(c)] = c["id"]
reposts = sum(1 for c in cars if last[rk(c)] != c["id"])
cars = [c for c in cars if last[rk(c)] == c["id"]]

# живые посты: не машины, но с текстом (отправка, осмотр, новости)
EMO = re.compile("[\U0001F000-\U0001FFFF←-⇿⌀-⏿☀-➿⬀-⯿️‼⁉‍⃣]")
news = []
seen = set()
JUNK = re.compile(r"music\.yandex|розыгрыш|uds\.app|программ\w* лояльност|нов\w* год|итоги|добиться своих целей|нужна ваша помощь|как вы относитесь|рассмотрели бы|активнее использовать вк|к сожалению, авто продан|снегоход|мото техник|wildberries|привезем авто из европы под ваш бюджет|немцы есть у нас|абсолютно новые автомоб")
CAROFFER = re.compile(r"Под\s*🔑|^\W*(Цена|✅\s*\d[\d,\s]{5,})|✔️\s*\d{4}\s*год|Цена\s*[Оо]т\s*\d", re.M)
CLIENTS = re.compile(r"осмотр|выкуплен|отправля|клиент|поздравля|миниобзор|приобрели|находка|регистрац")
MARKET = re.compile(r"утиль|госдум|законопроект|рын(ок|ка|ке)|санкц|дилер|представил|премьер|постановлен|аптечк|тонировк|первый автомобиль|автопробег|бренд|номер|вернутся в россию|средняя цена|старше 30 лет|покупки авто в европе|ждать больше не нужно|следующая глава|готовят свой")
for pid, p in sorted(posts.items(), reverse=True):
    if pid in car_ids or len(p["text"]) < 60: continue
    tl = p["text"].lower()
    if JUNK.search(tl) or CAROFFER.search(p["text"]): continue
    cat = "clients" if CLIENTS.search(tl) else "market" if MARKET.search(tl) else None
    if not cat: continue
    key = re.sub(r"\W+", "", tl)[:80]
    if key in seen: continue
    seen.add(key)
    imgs = []
    for i in range(1, len(p["photos"]) + 1):
        n = f"{pid}_{i:02d}"
        if webp(f"{D}/photos/{n}.jpg", f"{S}/p/{n}.webp", 800, 62): imgs.append(n)
    vt = p["videos"] and (os.path.exists(f"{S}/p/{pid}_v.webp") or vthumb(pid))
    if vt and webp(f"{D}/vthumbs/{pid}.jpg", f"{S}/p/{pid}_v.webp", 800, 62): imgs.insert(0, f"{pid}_v")
    if not imgs: continue
    t = p["text"]
    first = EMO.sub("", t.strip().split("\n")[0]).strip(" !,.")
    news.append({"id": pid, "date": p["date"][:10], "title": first[:90], "text": t, "img": imgs, "video": p["videos"] > 0, "cat": cat})

built = datetime.date.today().isoformat()
data = json.dumps({"cars": cars, "news": news, "built": built}, ensure_ascii=False, separators=(",", ":"))
tpl = open(ROOT + "/tools/template.html").read()
cfg = json.load(open(ROOT + "/config.json"))
tel = lambda x: "+" + re.sub(r"\D", "", x)
for k, v in {"NAME": cfg["name1"] + " " + cfg["name2"], "NAME1": cfg["name1"], "NAME2": cfg["name2"], "CITY": cfg["city"],
             "HOT": str(cfg.get("hot","")), "PICK": cfg.get("pick_photo",""), "LEGAL": cfg.get("legal",""), "LEAD": cfg.get("lead_url",""), "MANAGER": cfg["manager"], "PHONE1": cfg["phone1"], "PHONE2": cfg["phone2"], "TEL1": tel(cfg["phone1"]), "TEL2": tel(cfg["phone2"]),
             "ABOUT": cfg["about"], "VK": cfg["vk"], "VKSHORT": cfg["vk"].split("//")[-1], "CH": cfg["channel"], "INITIAL": cfg["name1"][0]}.items():
    tpl = tpl.replace("{{" + k + "}}", html.escape(v).replace("\n", "<br>"))
pe = lambda x: html.escape(x)
ava = lambda x: f'<img class="ava" src="{os.path.basename(x["photo"])}" alt="{pe(x["name"])}" width="56" height="56">' if x.get("photo") else f'<i>{pe(x["name"][0])}</i>'
people = "".join(f'<div class="person">{ava(x)}<div><b>{pe(x["name"])}</b><small>{pe(x.get("role",""))}</small>' + "".join(f'<a href="tel:{tel(ph)}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z"/></svg><span class="swap"><span>{pe(ph)}</span><span>Позвонить</span></span></a>' for ph in x["phones"]) + '</div></div>' for x in cfg.get("people", []))
if cfg.get("extra_phone"): people += f'<div class="xph">Если не дозвонились: <a href="tel:{tel(cfg["extra_phone"])}"><span class="swap"><span>{pe(cfg["extra_phone"])}</span><span>Позвонить</span></span></a></div>'
tpl = tpl.replace("<!--PEOPLE-->", people)
for x in cfg.get("people", []):
    if x.get("photo"): shutil.copy(D + "/" + x["photo"], S + "/" + os.path.basename(x["photo"]))
if os.path.exists(D + "/brand/logo.jpg") and shutil.which("sips"):
    for w in (96, 192): subprocess.run(["sips", "-z", str(w), str(w), D + "/brand/logo.jpg", "--out", f"{S}/logo{w}.png", "-s", "format", "png"], capture_output=True)
# фото удалённых в канале постов убираются с сайта
for sub in ("p", "t"):
    for f in os.listdir(f"{S}/{sub}"):
        if int(re.match(r"\d+", f).group()) not in posts: os.remove(f"{S}/{sub}/{f}")
open(S + "/index.html", "w").write(tpl.replace("/*DATA*/null", data))
open(S + "/robots.txt", "w").write("User-agent: *\nAllow: /\n")
sz = subprocess.run(["du", "-sh", S], capture_output=True, text=True).stdout.split()[0]
print(f"built: cars {len(cars)} (reposts dropped {reposts}) news {len(news)} photos {len(os.listdir(S + '/p'))} size {sz}")

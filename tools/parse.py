# posts.jsonl -> cars.json: разбор шаблонного поста в карточку машины.
import json, re, sys
src, out = sys.argv[1], sys.argv[2]
EMO = re.compile("[\U0001F000-\U0001FFFF←-⇿⌀-⏿☀-➿⬀-⯿️‼⁉‍⃣]")
TWO = {"land rover", "alfa romeo", "mercedes benz", "aston martin", "range rover", "lynk &"}
ORIG = {"Герман": "Германия", "Коре": "Корея", "Беларус": "Беларусь", "Белорус": "Беларусь", "Европ": "Европа",
        "Китa": "Китай", "Кита": "Китай", "Япон": "Япония", "Польш": "Польша", "Нидерланд": "Нидерланды",
        "Итали": "Италия", "Франци": "Франция", "Бельги": "Бельгия", "Швеци": "Швеция", "Литв": "Литва", "Эмират": "ОАЭ", "ОАЭ": "ОАЭ"}
MK = re.compile(r"\b(BMW|Mercedes|Audi|Volkswagen|VW|Volvo|Skoda|Ford|Opel|Land Rover|Range Rover|Kia|Peugeot|Renault|Citroen|Toyota|MINI|Mini|Hyundai|Mazda|Honda|Nissan|Subaru|Jaguar|Porsche|Chevrolet|Suzuki|Alfa Romeo|Genesis|Fiat|Lexus|GMC|Cupra|Mitsubishi|Bentley|Lotus|Geely|Alpina|Jeep|Lada|Haval|Chery|Tesla|Infiniti|Cadillac|Dodge|Seat|Smart)\b")
def num(s): return int(re.sub(r"\D", "", s)) if s and re.sub(r"\D", "", s) else None
cars, skipped = [], []
for line in open(src):
    p = json.loads(line)
    raw = p["text"]; t = EMO.sub("", raw)
    m = re.search(r"Цена\s*(?:в|от)?\s*:?\s*([\d][\d\s.,]*)\s*(₽|руб)", t, re.I)
    m0 = None if m else re.match(r"\s*(?:от\s*)?(\d[\d\s.,]{5,}\d)", t)
    yline = re.compile(r"^\s*(?:✔️|✔)?\s*(?:\d{1,2}\s*/\s*)?(?:19|20)\d\d\s*(?:год|г\b)")
    lines = [x for x in raw.split("\n") if x.strip()]
    yi = next((i for i, x in enumerate(lines) if yline.search(x)), None)
    has_star = "\u2b50" in raw
    if not p["photos"] or not (m or (has_star and re.search(r"Цена", t)) or (m0 and yi)):
        skipped.append(p["id"]); continue
    price = num((m or m0).group(1)) if (m or m0) else None
    if price and price < 10000: price *= 1000  # «3.290 тыс»
    if price and price < 300000: price = None
    star = [x for x in raw.split("\n") if "\u2b50" in x]
    picked = any("подобран" in x.lower() for x in star) or bool(re.search(r"Подобран по запросу", t, re.I))
    star = [x for x in star if "подобран" not in x.lower()]
    if not star: star = [x for x in lines if "\U0001F680" in x]
    if not star and yi: star = [lines[yi - 1]]
    name = re.sub(r"\s+", " ", EMO.sub("", star[0])).strip(" -:.…") if star else None
    if name:
        mk = MK.search(name)
        if mk: name = name[mk.start():]
    if not name:
        skipped.append(p["id"]); continue
    origin = next((v for k, v in ORIG.items() if re.search(r"Из\s+" + k, t)), None)
    dl = re.search(r"Доставка\s*(\d+\s*-\s*\d+|\d+)\s*(дн|день|дней|недел)", t)
    yr = re.search(r"(\d{1,2})\s*/\s*(\d{4})\s*г", t) or re.search(r"(?:^|\s)()(20\d\d|19\d\d)\s*г", t)
    mot = re.search(r"Мотор\s*([\d.,]+)\s*([А-Яа-яA-Za-z]+)?\s*/?\s*(\d+)?\s*л\.?\s*с", t) or re.search(r"Мотор\s*([\d.,]+)\s*([А-Яа-яA-Za-z()]+)()", t)
    elec = re.search(r"электро", t, re.I)
    drv = re.search(r"(Полный|Передний|Задний)\s+привод", t, re.I)
    box = re.search(r"\b(АКПП|AКПП|МКПП|Робот|Вариатор|DSG)\b", t, re.I)
    km = re.search(r"Пробег\s*([\d\s.,]+)\s*(тыс)?\.?\s*км", t)
    kmv = num(km.group(1)) if km else None
    if km and km.group(2): kmv = (kmv or 0) * 1000
    name = re.sub(r"^Мазда\b", "Mazda", name).replace("Mazda СХ", "Mazda CX")
    words = name.split()
    make = " ".join(words[:2]) if " ".join(words[:2]).lower().replace("-", " ") in TWO else words[0]
    make = {"Range Rover": "Land Rover", "Mercedes": "Mercedes-Benz", "VW": "Volkswagen", "Mersedes": "Mercedes-Benz", "BMV": "BMW", "Mini": "MINI", "Mini-Cooper": "MINI"}.get(make, make)
    cars.append({
        "picked": picked, "id": p["id"], "date": p["date"][:10] if p["date"] else None, "name": name, "make": make,
        "price": price, "origin": origin, "delivery": (dl.group(1).replace(" ", "") + (" нед." if dl.group(2).startswith("недел") else " дн.")) if dl else None,
        "month": int(yr.group(1)) if yr and yr.group(1) else None, "year": int(yr.group(2)) if yr else None,
        "volume": mot.group(1).replace(",", ".") if mot else None, "fuel": (mot.group(2) or "").lower() if mot else ("электро" if elec else None),
        "hp": num(mot.group(3)) if mot and mot.group(3) else None,
        "drive": drv.group(1).lower() if drv else None, "box": ("АКПП" if box and box.group(1).upper() in ("АКПП", "AКПП") else box.group(1)) if box else None,
        "km": kmv, "photos": len(p["photos"]), "videos": p["videos"],
    })
cars.sort(key=lambda c: -c["id"])
json.dump(cars, open(out, "w"), ensure_ascii=False)
miss = {k: sum(1 for c in cars if c[k] is None) for k in ("origin", "year", "volume", "hp", "drive", "box", "km", "delivery")}
print(f"cars {len(cars)} skipped {len(skipped)} missing {miss}")
print("skipped ids:", skipped[:40])

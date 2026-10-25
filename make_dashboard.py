#!/usr/bin/env python3
"""
Kindle Paperwhite（第7世代）用ダッシュボード画像を作るスクリプト。
- 画面サイズ: 1072 x 1448（縦置き）
- 内容: 日付・曜日 / 東京の今日と明日の天気 / 最終更新時刻
- 天気データ: Open-Meteo（無料・APIキー不要）
出力: dashboard.png（8bitグレースケール）
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

W, H = 1072, 1448
JST = timezone(timedelta(hours=9))

# 場所（東京）。別の場所にしたいときはここを変える
LAT, LON = 35.6895, 139.6917
PLACE = "東京"

OUT = os.environ.get("OUT", "dashboard.png")

FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ],
    "bold": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    ],
}


def font(weight, size):
    for path in FONT_CANDIDATES[weight] + FONT_CANDIDATES["regular"]:
        if os.path.exists(path):
            # index 0 = JP in Noto Sans CJK .ttc
            return ImageFont.truetype(path, size, index=0)
    sys.exit("日本語フォントが見つかりません")


WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def weather_label(code):
    """WMO天気コード → (日本語, アイコン種別)"""
    if code == 0:
        return "快晴", "sun"
    if code in (1, 2):
        return "晴れ時々くもり", "partly"
    if code == 3:
        return "くもり", "cloud"
    if code in (45, 48):
        return "霧", "cloud"
    if code in (51, 53, 55, 56, 57):
        return "霧雨", "rain"
    if code in (61, 63, 80, 81):
        return "雨", "rain"
    if code in (65, 82):
        return "大雨", "rain"
    if code in (66, 67):
        return "みぞれ", "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "雪", "snow"
    if code in (95, 96, 99):
        return "雷雨", "thunder"
    return "—", "cloud"


def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&timezone=Asia%2FTokyo&forecast_days=2"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        d = json.load(r)["daily"]
    days = []
    for i in range(2):
        days.append({
            "code": d["weather_code"][i],
            "max": round(d["temperature_2m_max"][i]),
            "min": round(d["temperature_2m_min"][i]),
            "pop": d["precipitation_probability_max"][i],
        })
    return days


# ---------- アイコン（絵文字フォントに頼らず線で描く） ----------

def draw_sun(dr, cx, cy, r, w):
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=w)
    import math
    for k in range(8):
        a = k * math.pi / 4
        x1, y1 = cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35
        x2, y2 = cx + math.cos(a) * r * 1.75, cy + math.sin(a) * r * 1.75
        dr.line([x1, y1, x2, y2], fill=0, width=w)


def draw_cloud(dr, cx, cy, s, w, fill=255):
    # s = 全体の幅の半分くらい
    parts = [
        (cx - s * 0.55, cy - s * 0.05, s * 0.38),
        (cx - s * 0.05, cy - s * 0.30, s * 0.50),
        (cx + s * 0.50, cy - s * 0.02, s * 0.36),
    ]
    base = [cx - s * 0.90, cy - s * 0.05, cx + s * 0.85, cy + s * 0.38]
    # 外枠
    for (x, y, r) in parts:
        dr.ellipse([x - r - w, y - r - w, x + r + w, y + r + w], fill=0)
    dr.rounded_rectangle([base[0] - w, base[1] - w, base[2] + w, base[3] + w], radius=s * 0.22, fill=0)
    # 中身
    for (x, y, r) in parts:
        dr.ellipse([x - r, y - r, x + r, y + r], fill=fill)
    dr.rounded_rectangle(base, radius=s * 0.20, fill=fill)


def draw_icon(dr, kind, cx, cy, size):
    w = max(4, size // 22)
    if kind == "sun":
        draw_sun(dr, cx, cy, size * 0.32, w)
    elif kind == "partly":
        draw_sun(dr, cx - size * 0.18, cy - size * 0.18, size * 0.22, w)
        draw_cloud(dr, cx + size * 0.08, cy + size * 0.12, size * 0.42, w)
    elif kind in ("cloud", "rain", "snow", "thunder"):
        oy = -size * 0.12 if kind != "cloud" else 0
        draw_cloud(dr, cx, cy + oy, size * 0.48, w)
        if kind == "rain":
            for k in (-1, 0, 1):
                x = cx + k * size * 0.22
                dr.line([x + size * 0.04, cy + size * 0.22, x - size * 0.04, cy + size * 0.40], fill=0, width=w)
        elif kind == "snow":
            for k in (-1, 0, 1):
                x, y, r = cx + k * size * 0.22, cy + size * 0.32, size * 0.04
                dr.ellipse([x - r, y - r, x + r, y + r], fill=0)
        elif kind == "thunder":
            pts = [(cx + size * 0.05, cy + size * 0.15), (cx - size * 0.08, cy + size * 0.32),
                   (cx + size * 0.02, cy + size * 0.32), (cx - size * 0.06, cy + size * 0.48)]
            dr.line(pts, fill=0, width=w, joint="curve")


def text_w(dr, s, f):
    b = dr.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def wrap(dr, s, f, max_w, max_lines):
    """日本語を1文字ずつ見て、幅に収まるよう折り返す"""
    no_start = "、。，．」』）】ー…!?！？ぁぃぅぇぉっゃゅょァィゥェォッャュョ"  # 行頭に来させない文字（禁則）
    lines, cur = [], ""
    for ch in s:
        if text_w(dr, cur + ch, f) > max_w and ch not in no_start:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def pick_book(now):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.json")
    try:
        with open(path, encoding="utf-8") as fp:
            books = json.load(fp)
    except Exception as e:
        print("books error:", e, file=sys.stderr)
        return None
    if not books:
        return None
    # 1日1冊、順番に入れ替わる
    return books[now.toordinal() % len(books)]


def render(now, days, book):
    img = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(img)
    M = 72  # 左右の余白
    CW = W - M * 2

    f_label = font("regular", 40)
    f_small = font("regular", 46)

    # ---- 日付 ----
    f_month = font("bold", 56)
    f_day = font("bold", 250)
    f_wd = font("bold", 88)
    dr.text((M, 60), f"{now.year}年 {now.month}月", font=f_month, fill=0)
    dr.text((M - 8, 100), f"{now.day}", font=f_day, fill=0)
    day_w = text_w(dr, f"{now.day}", f_day)
    wd = WEEKDAYS[now.weekday()]
    dr.text((M + day_w + 40, 255), f"{wd}曜日", font=f_wd, fill=0)

    # ---- 今日の天気 ----
    y0 = 430
    dr.line([M, y0, W - M, y0], fill=0, width=4)
    dr.text((M, y0 + 30), f"今日の{PLACE}", font=f_label, fill=60)
    if days:
        t = days[0]
        label, kind = weather_label(t["code"])
        draw_icon(dr, kind, M + 130, y0 + 245, 250)
        x = M + 300
        dr.text((x, y0 + 95), label, font=font("bold", 62), fill=0)
        f_temp = font("bold", 104)
        dr.text((x, y0 + 170), f"{t['max']}°", font=f_temp, fill=0)
        mx_w = text_w(dr, f"{t['max']}°", f_temp)
        dr.text((x + mx_w + 24, y0 + 225), f"/ {t['min']}°", font=f_small, fill=0)
        dr.text((x, y0 + 310), f"降水確率 {t['pop']}%", font=f_small, fill=0)

        # 明日（1行で）
        if len(days) > 1:
            t2 = days[1]
            label2, kind2 = weather_label(t2["code"])
            y = y0 + 420
            dr.text((M, y), "明日", font=f_label, fill=60)
            draw_icon(dr, kind2, M + 160, y + 26, 80)
            dr.text((M + 220, y - 6),
                    f"{label2}  {t2['max']}°/{t2['min']}°  降水{t2['pop']}%",
                    font=font("regular", 44), fill=0)
    else:
        dr.text((M, y0 + 140), "天気を取得できませんでした", font=f_small, fill=0)

    # ---- 今日の一冊 ----
    y1 = 940
    dr.line([M, y1, W - M, y1], fill=0, width=4)
    if book:
        dr.text((M, y1 + 30), f"今日の一冊（{book.get('genre', '')}）", font=f_label, fill=60)
        title = f"『{book['title']}』"
        f_title = font("bold", 64)
        lines = wrap(dr, title, f_title, CW, 2)
        step = 82
        if len(lines) > 1:  # 長いタイトルは少し小さく
            f_title = font("bold", 50)
            lines = wrap(dr, title, f_title, CW, 2)
            step = 64
        y = y1 + 100
        for line in lines:
            dr.text((M, y), line, font=f_title, fill=0)
            y += step
        dr.text((M, y + 4), book["author"], font=font("regular", 46), fill=0)
        y += 86
        f_note = font("regular", 40)
        for line in wrap(dr, book.get("note", ""), f_note, CW, 3):
            dr.text((M, y), line, font=f_note, fill=40)
            y += 58

    # ---- 更新時刻 ----
    f_upd = font("regular", 34)
    s = f"更新 {now:%H:%M}"
    dr.text((W - M - text_w(dr, s, f_upd), H - 80), s, font=f_upd, fill=90)

    return img


def main():
    now = datetime.now(JST)
    if os.environ.get("SAMPLE"):
        days = [{"code": 2, "max": 22, "min": 14, "pop": 10},
                {"code": 61, "max": 19, "min": 13, "pop": 70}]
    else:
        try:
            days = fetch_weather()
        except Exception as e:  # 天気が取れなくても日付だけは出す
            print("weather error:", e, file=sys.stderr)
            days = []
    render(now, days, pick_book(now)).save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()

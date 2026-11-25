"""Append the user's requested summary to report.md: what was left out, average time per photo/video,
split by route and by era (count and screen time)."""
import csv
from collections import Counter, defaultdict
from common import OUT
from show_plan import load

rows, photo_ms = load()
inv = list(csv.DictReader(open(OUT / "inventory.csv", encoding="utf-8-sig")))
sel = list(csv.DictReader(open(OUT / "selection_log.csv", encoding="utf-8-sig")))
total = sum(r["ms"] for r in rows) / 1000
vids = [r for r in rows if r["סוג"] == "וידאו"]

def table(key, title):
    n, s = Counter(), defaultdict(float)
    for r in rows:
        n[r[key]] += 1
        s[r[key]] += r["ms"] / 1000
    out = [f"### {title}", "", "| | פריטים | % | זמן מסך | % |", "|---|---|---|---|---|"]
    for k in sorted(n, key=lambda k: -n[k]):
        out.append(f"| {k} | {n[k]} | {n[k] / len(rows):.0%} | {int(s[k]) // 60}:{int(s[k]) % 60:02d} | {s[k] / total:.0%} |")
    return out + [""]

files = [r for r in inv if not r["reason"].startswith("zip")]
media_found = [r for r in files if r["status"] != "skipped"]
L = ["", "## סיכום למשתמש", "",
     f"- **אורך:** {int(total) // 60}:{int(total) % 60:02d} דקות – בדיוק אורך 5 השירים ברצף (עם דעיכה ב־4 השניות האחרונות).",
     f"- **זמן ממוצע:** תמונה {photo_ms / 1000:.2f} שניות (כולן שוות); סרטון {sum(r['ms'] for r in vids) / 1000 / len(vids):.1f} שניות "
     f"בממוצע ({min(r['ms'] for r in vids) / 1000:.1f}–{max(r['ms'] for r in vids) / 1000:.1f}), סך הכול {sum(r['ms'] for r in vids) / 1000:.0f} שניות וידאו.",
     f"- **נכנסו:** {len(rows)} פריטים ({len(rows) - len(vids)} תמונות, {len(vids)} סרטונים) מתוך {len(media_found)} תמונות וסרטונים שנמצאו בדרייב.",
     "", "### מה לא נכנס", "",
     f"- כפילויות מדויקות (אותה תמונה פעמיים, גם בגודל אחר): {sum(r['status'] == 'duplicate' for r in inv)}",
     f"- תמונות כמעט זהות (צילומי רצף / אותו רגע): {sum(r['status'] == 'similar' for r in inv)}",
     f"- הוצאו בסקירה הוויזואלית (מטושטשות, חוזרות על אותו רגע, פחות מעניינות, קטעי וידאו כפולים): "
     f"{sum(r['נבחר'] == 'לא' and r['סימון'] == 'X' for r in sel)}",
     f"- טובות אבל מחוץ למכסה (כדי לשמור על ⅓ ישן / ⅔ חדש ועל איזון בין השולחים): "
     f"{sum(r['נבחר'] == 'לא' and r['סימון'] != 'X' for r in sel)}",
     "- לא חומר למצגת: הסרטון המלא של מצגת גלית רוזן (התוכן שלו נכנס דרך 'תמונות מתוך גלית רוזן'), 5 השירים (מוזיקת רקע).",
     "- הרשימה המלאה, קובץ־קובץ עם הסיבה: `selection_log.csv` ו־`inventory.csv`.", "",
     "### התפלגות", "", *table("מסלול", "לפי מסלול"), *table("תקופה", "לפי זמן צילום (ישן = מצגת גלית רוזן, לפני כשנתיים; חדש = כל השאר)"),
     *table("סוג", "לפי סוג"), *table("קטגוריה", "לפי קטגוריה"), *table("שולח", "לפי שולח")]
with open(OUT / "report.md", "a", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("\n".join(L))

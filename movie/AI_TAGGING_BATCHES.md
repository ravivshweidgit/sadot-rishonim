# 📦 תיוג בחלקים (Batches) - אם הקובץ גדול מדי

## מתי צריך לעבוד בחלקים?

אם הקובץ `pages_for_ai_tagging.json` גדול מדי (יותר מ-10MB או יותר מ-100 עמודים), 
אפשר לפצל אותו לחלקים קטנים יותר.

**הערה:** הקובץ מכיל עמודים עם שורות ממוספרות, וכל עמוד צריך להיות מתוייג עם טווחי שורות.

---

## איך לעבוד בחלקים:

### שלב 1: פיצול הקובץ

**אפשרות A: לפי ספר**
- חלק 1: כל עמודים מ-"שדות ראשונים"
- חלק 2: כל עמודים מ-"בית מרקובסקי"

**אפשרות B: לפי שנים**
- חלק 1: עמודים משנים 1900-1910
- חלק 2: עמודים משנים 1911-1921

**אפשרות C: לפי כמות**
- חלק 1: עמודים 1-100
- חלק 2: עמודים 101-200
- חלק 3: עמודים 201-276

---

### שלב 2: תיוג כל חלק בנפרד

שלח כל חלק ל-AI בנפרד עם אותן הוראות.

**דוגמה:**
```
קח את הקובץ JSON הזה (חלק 1 מתוך 3).
זה מכיל עמודים 1-100 משני הספרים.

לכל עמוד, תייג טווחי שורות עם:
- line_start, line_end, year, month, location, locations, characters, confidence

(אותן הוראות כמו ב-AI_TAGGING_INSTRUCTIONS.md)
```

---

### שלב 3: איחוד התוצאות

לאחר שכל החלקים מתויגים:

1. קח את כל הקבצים המתויגים
2. איחד אותם לקובץ אחד: `pages_tagged_by_ai.json`
3. ודא שהמבנה תקין (כל העמודים שם)

---

## סקריפט עזר לאיחוד:

אם יש לך כמה קבצים מתויגים, אתה יכול לאחד אותם:

```python
import json
from pathlib import Path

# קבצים מתויגים
files = [
    'pages_tagged_part1.json',
    'pages_tagged_part2.json',
    'pages_tagged_part3.json'
]

all_pages = []
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        all_pages.extend(data.get('pages', []))

# שמור קובץ מאוחד
output = {
    'metadata': {
        'generated_at': datetime.now().isoformat(),
        'total_pages': len(all_pages),
        'books': ['sadot_rishonim', 'beit_markovski'],
        'method': 'batched_tagging'
    },
    'pages': all_pages
}

with open('pages_tagged_by_ai.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
```

---

## 💡 המלצה:

**בדרך כלל לא צריך!** 

רוב מודלי AI (ChatGPT-4, Claude 3.5) יכולים לטפל ב-276 עמודים בבת אחת.

**נסה קודם את כל הקובץ בבת אחת.** רק אם AI לא מצליח, פצל לחלקים.

---

## ✅ בדיקה:

לפני שאתה ממשיך ל-MERGE, ודא:
- [ ] כל העמודים מתויגים עם `line_tags`
- [ ] אין כפילויות
- [ ] המבנה JSON תקין
- [ ] כל טווח יש לו `line_start`, `line_end`, `year` ו-`location` (או null)
- [ ] כל השורות הלא-ריקות מכוסות (או לפחות רוב השורות)

אם הכל תקין, המשך ל-MERGE! 🎯

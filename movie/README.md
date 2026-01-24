# פרויקט סרט AI - מטולה 1900-1921

## מטרת הפרויקט
יצירת סרט AI המספר את סיפור המשפחה והחיים במטולה בשנים 1900-1921, 
בהתבסס על הספרים "שדות ראשונים" ו"בית מרקובסקי".

## הגישה: AI מתייג → AI קובע insertion points → Python ממזג

**הגישה הנבחרת:** 
1. AI מתייג טווחי שורות בתוך עמודים (שנה, חודש, מיקום)
2. AI מחלק את הספר של רוחמה לפסקאות וקובע insertion points (לכל פסקה, איפה להיכנס בספר של יהודה)
3. Python ממזג לפי insertion points (שומר על הסדר המקורי של הספר של יהודה)

**למה?**
- ✅ הספר של יהודה נשאר בסדר המקורי שלו (מסגרת הנרטיב נשמרת)
- ✅ AI מבין את ההקשר הכרונולוגי והנרטיבי בין שני הספרים
- ✅ פסקאות מהספר של רוחמה נכנסות בנקודות המתאימות לפי הקשר, לא רק לפי זמן
- ✅ שמירה על רצף פסקתי בספר של רוחמה
- ✅ זיהוי מדויק מאוד (AI מבין הקשר)
- ✅ התסריט = הטקסט מהספרים עצמם
- ✅ Python עובד עם מבנה שהוא מבין (עמודים ושורות ממוספרות)
- ✅ שמירה על הקשר מדויק - כל קטע יודע מאיזה עמוד ואילו שורות

## מבנה הפרויקט

```
movie/
├── data/           # נתונים גולמיים (תמונות)
│   ├── faces/      # תמונות פנים של הדמויות
│   ├── locations/ # תמונות ארכיון מקומות
│   └── archive/    # תמונות נוספות לא מסווגות
├── scripts/        # סקריפטים לעיבוד
│   ├── 01_tag_pages_with_ai.py              # שלב 1: יוצר תבנית לתיוג
│   ├── 02_tag_pages_with_gemini.py          # שלב 2: מתייג עם Gemini API
│   ├── 02b_determine_insertion_points.py    # שלב 2b: AI קובע insertion points (חלוקה לפסקאות)
│   └── 03_merge_books_with_ai_tags.py       # שלב 3: ממזג לפי insertion points
├── config/         # הגדרות
├── models/         # מודלים מאומנים
├── output/         # תוצרים
└── docs/           # תיעוד
```

## 🚀 התחלה מהירה

**👉 התחל כאן:** [GETTING_STARTED.md](GETTING_STARTED.md) - מדריך פשוט וברור להתחלה!

### הצעדים הבסיסיים:

1. **יצירת תבנית לתיוג:**
   ```bash
   cd movie/scripts
   python 01_tag_pages_with_ai.py
   ```

2. **תיוג עם AI (אוטומטי עם Gemini API):**
   ```bash
   python 02_tag_pages_with_gemini.py
   ```
   
   **או תיוג ידני:**
   - פתח את `movie/output/scripts/pages_for_ai_tagging.json`
   - שלח ל-ChatGPT/Claude לתיוג (ראה [AI_TAGGING_INSTRUCTIONS.md](AI_TAGGING_INSTRUCTIONS.md))
   - שמור כ-`pages_tagged_by_ai.json`

3. **קביעת insertion points (AI מחלק לפסקאות):**
   ```bash
   python 02b_determine_insertion_points.py
   ```
   
   AI מחלק את הספר של רוחמה לפסקאות וקובע לכל פסקה איפה להיכנס בספר של יהודה.

4. **מיזוג לפי insertion points:**
   ```bash
   python 03_merge_books_with_ai_tags.py
   ```

**תוצאה:** `merged_books_with_ai_tags.txt` - הטקסט הממוזג עם הסדר המקורי של הספר של יהודה ופסקאות מהספר של רוחמה בנקודות המתאימות

## 📚 מסמכים חשובים

- **[GETTING_STARTED.md](GETTING_STARTED.md)** ⭐ - התחלה מהירה (קרא קודם!)
- **[AI_TAGGING_APPROACH.md](AI_TAGGING_APPROACH.md)** ⭐⭐ - הגישה המשולבת: AI מתייג טווחי שורות → Python ממזג
- **[AI_TAGGING_INSTRUCTIONS.md](AI_TAGGING_INSTRUCTIONS.md)** - הוראות מפורטות לתיוג טווחי שורות עם AI
- **[WORKFLOW.md](WORKFLOW.md)** - סדר עבודה מפורט שלב אחר שלב
- **[SCENE_GENERATION_PLAN.md](SCENE_GENERATION_PLAN.md)** 🎬 - תכנית בניית סצנות (שלב 2, אחרי MERGE)

## 📖 תיעוד נוסף
- [docs/CHARACTERS.md](docs/CHARACTERS.md) - תיעוד דמויות
- [docs/LOCATIONS.md](docs/LOCATIONS.md) - תיעוד מקומות
- [docs/README.md](docs/README.md) - סקירת תיעוד טכני

## 📦 מסמכים בארכיון

מסמכים ישנים שהועברו לארכיון (לא רלוונטיים לגישה הנוכחית):
- `archive/old_approaches/` - גישות ישנות
- `docs/archive/` - תיעוד טכני ישן
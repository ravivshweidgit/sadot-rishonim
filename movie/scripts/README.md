# סקריפטים - פרויקט סרט AI מטולה

## סקריפטים רלוונטיים (הגישה הנוכחית)

### שלב 1: יצירת תבנית לתיוג
**`01_tag_pages_with_ai.py`**
- יוצר קובץ JSON עם כל העמודים מוכן לתיוג
- תוצאה: `pages_for_ai_tagging.json`

### שלב 2: תיוג עם Gemini API
**`02_tag_pages_with_gemini.py`** ⭐
- מתייג כל עמוד אוטומטית עם Gemini API
- משתמש ב-API key מ-`python/api_key.txt`
- תוצאה: `pages_tagged_by_ai.json`

### שלב 2b: קביעת insertion points (חלוקה לפסקאות)
**`02b_determine_insertion_points.py`** ⭐
- AI מחלק את הספר של רוחמה לפסקאות בעלות הקשר (contextually coherent paragraphs)
- לכל פסקה, AI קובע איפה היא צריכה להיכנס בספר של יהודה (עמוד + שורה)
- AI קורא את הספר של יהודה במלואו כדי להבין את ההקשר הכרונולוגי והנרטיבי
- משתמש ב-API key מ-`python/api_key.txt`
- תוצאה: `insertion_points.json` - ברמת פסקאות

### שלב 3: מיזוג לפי insertion points
**`03_merge_books_with_ai_tags.py`**
- ממזג את שני הספרים לפי insertion points שקבע AI
- שומר על הסדר המקורי של הספר של יהודה (שדות ראשונים)
- מכניס קטעים מהספר של רוחמה בנקודות שקבע AI
- תוצאה: `merged_books_with_ai_tags.txt` (התסריט!)
- **הערה:** אם אין `insertion_points.json`, הסקריפט ישתמש במיון כרונולוגי (שיטה ישנה) כגיבוי.

---

## סקריפטים בארכיון

הסקריפטים הבאים הועברו לארכיון כי הם עובדים עם הגישה הישנה:

- `archive/old_scripts/combine_scenes.py` - עובד עם `merged_scenes.json` (גישה ישנה)
- `archive/old_scripts/generate_narration.py` - עובד עם `merged_scenes.json` (גישה ישנה)
- `archive/old_scripts/generate_video.py` - עובד עם `merged_scenes.json` (גישה ישנה)
- `archive/old_scripts/create_movie_with_narration.md` - מסמך על הגישה הישנה

**הערה:** הסקריפטים האלה ייתכן שיעודכנו בעתיד לעבוד עם הגישה החדשה (`merged_books_with_ai_tags.txt`).

---

## סדר הרצה מומלץ

```bash
cd movie/scripts

# שלב 1: יצירת תבנית
python 01_tag_pages_with_ai.py

# שלב 2: תיוג אוטומטי
python 02_tag_pages_with_gemini.py

# שלב 2b: קביעת insertion points
python 02b_determine_insertion_points.py

# שלב 3: מיזוג לפי insertion points
python 03_merge_books_with_ai_tags.py
```

---

## תוצאות

כל התוצאות נשמרות ב-`movie/output/scripts/`:
- `pages_for_ai_tagging.json` - תבנית לתיוג
- `pages_tagged_by_ai.json` - עמודים מתויגים
- `insertion_points.json` - נקודות הכנסה שקבע AI
- `merged_books_with_ai_tags.txt` - התסריט הממוזג! 🎬

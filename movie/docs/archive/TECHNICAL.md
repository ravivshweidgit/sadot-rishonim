# תיעוד טכני - Technical Documentation

## סקריפטים

### extract_scenes.py
**מטרה:** חילוץ סצנות מהספרים

**פונקציונליות:**
- קורא קבצי טקסט מהספרים
- מזהה דמויות, מקומות, ותאריכים
- יוצר מבנה JSON מובנה
- מסנן סצנות רלוונטיות לתקופה 1900-1921

**שימוש:**
```bash
cd movie/scripts
python extract_scenes.py
```

**פלט:**
- `movie/output/scripts/scenes.json`

**מבנה הפלט:**
```json
{
  "metadata": {
    "generated_at": "2024-...",
    "total_scenes": 195,
    "books_processed": ["sadot_rishonim", "beit_markovski"],
    "time_period": "1900-1921"
  },
  "scenes": [
    {
      "id": "sadot_rishonim_page_009",
      "book_id": "sadot_rishonim",
      "page_number": 9,
      "chapter": "ראשית",
      "year": 1904,
      "characters": ["yehuda", "yosef"],
      "locations": ["metula", "jaffa"],
      "description": "...",
      "full_text": "...",
      "visual_requirements": {...}
    }
  ]
}
```

## מבנה נתונים

### Characters (characters.json)
- מגדיר את כל הדמויות
- כולל מידע על גילאים, מקומות, תפקידים

### Locations (locations.json)
- מגדיר את כל המקומות
- כולל תיאורים ותכונות

### Scenes (scenes.json)
- נוצר על ידי extract_scenes.py
- מכיל את כל הסצנות מהספרים

## טכנולוגיות מומלצות

### Face Learning
- `insightface` - Face recognition & embedding
- `face_recognition` - Python face recognition library
- `MediaPipe` - Face detection

### Video Generation
- `Runway Gen-3` - High quality video generation
- `Stable Video Diffusion` - Open source alternative
- `AnimateDiff` - Animation from images
- `ComfyUI` - Workflow orchestration

### Face Swapping
- `roop` / `FaceSwap` - Face swapping
- `DeepFaceLab` - Advanced face swapping

### Image Processing
- `PIL/Pillow` - Image manipulation
- `OpenCV` - Computer vision
- `numpy` - Numerical operations

## Workflow

1. **Data Collection** - איסוף תמונות
2. **Image Processing** - עיבוד תמונות
3. **Script Extraction** - חילוץ סצנות (✅ הושלם)
4. **Video Generation** - יצירת וידאו
5. **Post-Production** - פוסט-פרודקשן

## בעיות ידועות ופתרונות

### בעיה: זיהוי דמויות לא מדויק
**פתרון:** שיפור רשימת CHARACTERS בסקריפט, הוספת שמות חלופיים

### בעיה: זיהוי מקומות לא מדויק
**פתרון:** שיפור רשימת LOCATIONS, הוספת וריאציות שמות

### בעיה: זיהוי תאריכים לא מדויק
**פתרון:** שיפור patterns, הוספת הקשר מהפרקים

## שיפורים עתידיים

1. שיפור זיהוי דמויות עם AI
2. שיפור זיהוי מקומות עם AI
3. יצירת תסריט ויזואלי מפורט יותר
4. אינטגרציה עם כלי יצירת וידאו

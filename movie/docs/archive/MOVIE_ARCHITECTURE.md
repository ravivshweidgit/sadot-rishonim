# ארכיטקטורת הסרט - Movie Architecture

## עקרון יסוד: הקריינות מניעה את הסרט

הסרט בנוי כך ש**הקריינות מהספרים היא הבסיס והמניע הראשי**, והוידאו מתאים לה.

```
קריינות (מהספרים) → מניעה → וידאו (מתאים לקריינות)
```

## מבנה הסרט

### 1. יחידת בסיס: סצנה עם קריינות

כל סצנה היא יחידה עצמאית שכוללת:

```
┌─────────────────────────────────────┐
│         סצנה (Scene)                │
├─────────────────────────────────────┤
│ • ID: scene_001                     │
│ • Narration Audio: scene_001.mp3   │
│   └─ Duration: 45 seconds          │
│ • Video: scene_001.mp4              │
│   └─ Duration: 45 seconds (מסונכרן)│
│ • Visual Content:                  │
│   - Background (מתמונות ארכיון)    │
│   - Characters (עם פנים מזוהות)    │
│   - Actions (לפי הטקסט)            │
└─────────────────────────────────────┘
```

### 2. תהליך יצירה (Workflow)

```
┌─────────────────────────────────────────────────────────┐
│ שלב 1: חילוץ ומיזוג סצנות                              │
├─────────────────────────────────────────────────────────┤
│ • extract_scenes.py → scenes.json                      │
│ • merge_scenes_from_books.py → merged_scenes.json      │
│   └─ כל סצנה כוללת:                                    │
│      - narration_text (טקסט מהספרים)                  │
│      - narration_duration_estimate (משך משוער)          │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ שלב 2: יצירת קריינות (TTS)                            │
├─────────────────────────────────────────────────────────┤
│ • generate_narration.py → *.mp3 files                  │
│   └─ כל סצנה מקבלת קובץ קריינות                       │
│   └─ הקריינות היא הבסיס - היא קובעת את הקצב          │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ שלב 3: יצירת וידאו (מסונכרן לקריינות)                 │
├─────────────────────────────────────────────────────────┤
│ • generate_video.py → *.mp4 files                       │
│   └─ לכל סצנה:                                         │
│      1. טוען את קובץ הקריינות                          │
│      2. קורא את משך הקריינות (duration)               │
│      3. יוצר וידאו באותו משך בדיוק                     │
│      4. מסונכרן את התוכן הויזואלי עם הקריינות         │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ שלב 4: חיבור לסרט אחד                                  │
├─────────────────────────────────────────────────────────┤
│ • combine_scenes.py → final_movie.mp4                  │
│   └─ מחבר את כל הסצנות לפי סדר כרונולוגי              │
│   └─ מחבר את כל הקריינות ברצף                          │
│   └─ מוסיף transitions בין סצנות                       │
└─────────────────────────────────────────────────────────┘
```

## עקרונות עיצוב

### עקרון 1: הקריינות קובעת את הקצב

**לא:** יצירת וידאו ואז הוספת קריינות  
**כן:** יצירת קריינות ואז התאמת הוידאו אליה

```python
# נכון ✅
narration_duration = get_audio_duration("scene_001.mp3")  # 45 seconds
video = create_video(duration=narration_duration)  # וידאו באותו משך

# לא נכון ❌
video = create_video(duration=30)  # וידאו קבוע
narration = fit_audio_to_video(video)  # קריינות מתאימה לוידאו
```

### עקרון 2: כל סצנה עצמאית

כל סצנה היא יחידה עצמאית עם:
- קריינות משלה
- וידאו משלה
- סינכרון מושלם ביניהן

זה מאפשר:
- עריכה קלה של סצנות בודדות
- החלפה/הסרה של סצנות
- בדיקה נפרדת של כל סצנה

### עקרון 3: סינכרון מושלם

הסרט צריך להיות מסונכרן כך ש:
- כל מילה בקריינות מתאימה למה שרואים בוידאו
- אם הקריינות מדברת על "יהודה כילד" - הוידאו מראה את יהודה כילד
- אם הקריינות מדברת על "מטולה" - הוידאו מראה את מטולה

## מבנה קבצים

```
movie/
├── output/
│   ├── scripts/
│   │   ├── scenes.json              # סצנות נפרדות
│   │   └── merged_scenes.json       # סצנות משולבות עם קריינות
│   │
│   ├── narration/                   # קריינות (TTS)
│   │   ├── scene_001_narration.mp3
│   │   ├── scene_002_narration.mp3
│   │   ├── ...
│   │   └── narration_index.json     # אינדקס עם משכי זמן
│   │
│   ├── scenes/                      # סצנות וידאו בודדות
│   │   ├── scene_001.mp4            # מסונכרן עם scene_001_narration.mp3
│   │   ├── scene_002.mp4
│   │   └── ...
│   │
│   └── final/
│       └── movie_metula_1900_1921.mp4  # סרט סופי עם קריינות
```

## תהליך יצירת סצנה בודדת

### שלב 1: הכנת הקריינות
```python
# 1. קרא את הטקסט מהסצנה
narration_text = scene['narration_text']

# 2. צור קריינות (TTS)
audio_file = generate_tts(narration_text, "scene_001.mp3")

# 3. קרא את משך הקריינות
duration = get_audio_duration(audio_file)  # לדוגמה: 45 seconds
```

### שלב 2: יצירת וידאו מסונכרן
```python
# 1. קרא את ה-AI Prompt מהסצנה
ai_prompt = scene['ai_prompt']
visual_req = scene['visual_requirements']

# 2. בחר תמונות רפרנס
background_image = select_location_image(visual_req['setting'])
character_faces = load_character_faces(visual_req['characters'])

# 3. צור וידאו באותו משך כמו הקריינות
video = generate_video(
    prompt=ai_prompt,
    background=background_image,
    characters=character_faces,
    duration=duration,  # בדיוק כמו משך הקריינות!
    action=visual_req['action']
)

# 4. שמור את הוידאו
save_video(video, "scene_001.mp4")
```

### שלב 3: סינכרון
```python
# חבר את הקריינות והוידאו
final_scene = combine_audio_video(
    video="scene_001.mp4",
    audio="scene_001_narration.mp3",
    output="scene_001_final.mp4"
)
```

## חיבור סצנות לסרט

```python
# 1. טען את כל הסצנות לפי סדר כרונולוגי
scenes = load_scenes_sorted_by_year()

# 2. חבר את כל הקריינות ברצף
combined_audio = concatenate_audio([
    scene['narration_file'] for scene in scenes
])

# 3. חבר את כל הוידאו ברצף (עם transitions)
combined_video = concatenate_video([
    scene['video_file'] for scene in scenes
], transitions=True)

# 4. חבר את הקריינות והוידאו
final_movie = combine_audio_video(
    video=combined_video,
    audio=combined_audio,
    output="movie_metula_1900_1921.mp4"
)
```

## יתרונות הארכיטקטורה הזו

### 1. דיוק היסטורי
- הקריינות מהספרים מבטיחה שהסרט מדויק
- הוידאו מתאים לטקסט, לא להפך

### 2. גמישות
- קל להוסיף/להסיר סצנות
- קל לערוך סצנה בודדת
- קל להחליף קריינות או וידאו

### 3. איכות
- כל סצנה מסונכרנת מושלם
- הקריינות והוידאו תואמים זה לזה

### 4. תחזוקה
- קל לזהות בעיות (סצנה ספציפית)
- קל לתקן (רק את הסצנה הבעייתית)

## דוגמה: סצנה מלאה

```json
{
  "id": "merged_1904_jaffa",
  "year": 1904,
  "location": "jaffa",
  
  "narration_text": "[משדות ראשונים]\nיהודה מור עלה ארצה כילד ב-1904...\n\n[מבית מרקובסקי]\nבעיצומו של חורף תרס\"ד (1904) עגנה אוניה בחוף ימה של יפו...",
  
  "narration_file": "output/narration/merged_1904_jaffa_narration.mp3",
  "narration_duration": 45,  // seconds
  
  "video_file": "output/scenes/merged_1904_jaffa.mp4",
  "video_duration": 45,  // בדיוק כמו הקריינות!
  
  "visual_requirements": {
    "setting": "jaffa",
    "characters": ["yehuda", "yosef", "moriah"],
    "action": "arrival",
    "mood": "joyful"
  }
}
```

## סיכום

**הקריינות מהספרים היא הלב של הסרט:**
1. היא קובעת את הקצב
2. היא קובעת את התוכן
3. היא קובעת את המשך
4. הוידאו מתאים לה, לא להפך

**התוצאה:** סרט שמספר את הסיפור מהספרים, עם וידאו שמתאים מושלם לטקסט.

# AI Chat Feature - שיחה עם יהודה

תכונת שיחה עם יהודה מרקובסקי באמצעות Gemini AI.

## הגדרה ראשונית

### 1. התקנת תלויות

```bash
npm install
```

### 2. קבלת Gemini API Key

1. היכנס ל-[Google AI Studio](https://makersuite.google.com/app/apikey)
2. צור API key חדש
3. העתק את המפתח

### 3. הגדרת משתנה סביבה

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

**Windows (CMD):**
```cmd
set GEMINI_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

או צור קובץ `.env` בתיקיית הפרויקט:
```
GEMINI_API_KEY=your_api_key_here
```

### 4. הפעלת השרת

```bash
npm start
```

השרת ירוץ על `http://localhost:3000`

## שימוש

1. פתח את האתר בדפדפן: `http://localhost:3000`
2. לחץ על הכפתור "💬 שיחה עם יהודה" בפינה השמאלית התחתונה
3. שאל שאלות בעברית על חייו של יהודה מרקובסקי, מטולה, נהלל, וכו'

## תכונות

- **שיחה בגוף ראשון**: ה-AI מגיב כפי שיהודה עצמו היה מגיב
- **ציטוטי עמודים**: התשובות כוללות הפניות לעמודים בספר
- **קישורים לעמודים**: לחיצה על "עמוד X" מעבירה לקורא לעמוד המתאים
- **היסטוריית שיחה**: השיחה נשמרת במהלך הסשן
- **עיצוב RTL**: מותאם לעברית וכיוון מימין לשמאל

## API Endpoints

### POST /api/chat
שולח הודעה ל-AI ומקבל תגובה.

**Request:**
```json
{
  "message": "ספר לי על מטולה",
  "conversationHistory": [
    { "role": "user", "content": "שלום" },
    { "role": "assistant", "content": "שלום! איך אני יכול לעזור?" }
  ]
}
```

**Response:**
```json
{
  "response": "כפי שסיפרתי בעמוד 9, מטולה היא מושבה קטנה...",
  "citations": [9, 26],
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### POST /api/refresh-cache
מרענן את מטמון קבצי הטקסט (כשמוסיפים קבצים חדשים).

### GET /api/health
בודק את סטטוס השרת והמטמון.

## פתרון בעיות

### ה-AI לא עובד
- ודא ש-`GEMINI_API_KEY` מוגדר נכון
- בדוק את הקונסול למידע על שגיאות
- ודא שהשרת רץ על פורט 3000

### תשובות לא מדויקות
- ודא שכל קבצי הטקסט בתיקיית `/text` תקינים
- רענן את המטמון באמצעות `/api/refresh-cache`

### בעיות CORS
- ודא שאתה משתמש בשרת Node.js ולא פותח את הקבצים ישירות
- השרת מטפל ב-CORS אוטומטית

## הערות טכניות

- השרת קורא את כל קבצי הטקסט בעת ההפעלה
- המטמון מתעדכן רק בעת רענון ידני או הפעלה מחדש של השרת
- היסטוריית השיחה מוגבלת ל-10 הודעות אחרונות
- כל תגובה כוללת את כל קבצי הטקסט כקונטקסט (Gemini Long-Context)


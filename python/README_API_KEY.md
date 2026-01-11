# API Key Setup

This project uses Google Gemini API for OCR and text processing. For security, the API key is stored locally and not committed to git.

## Setup Instructions

1. **Get your API key:**
   - Go to https://aistudio.google.com/apikey
   - Sign in with your Google account
   - Click "Create API Key" or "+ Create API Key"
   - Select or create a Google Cloud project
   - Copy your API key

2. **Add the API key:**
   - Open `python/api_key.txt`
   - Paste your API key on a new line (without quotes)
   - Save the file

3. **Verify it works:**
   - Run any of the Python scripts (e.g., `python ocr_pdfs.py`)
   - If the API key is valid, the script will run successfully

## Security Notes

- ✅ `api_key.txt` is in `.gitignore` - it will NOT be committed to git
- ✅ Never share your API key publicly
- ✅ If your API key is leaked, create a new one immediately
- ✅ You can also set the `GEMINI_API_KEY` environment variable as an alternative

## Troubleshooting

If you get an error about the API key:
1. Make sure `api_key.txt` exists in the `python/` directory
2. Make sure the API key is on its own line (no quotes, no extra spaces)
3. Make sure the API key starts with `AIzaSy`
4. Try creating a new API key if the old one was leaked

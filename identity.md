# Project Name: sadot_rishonim

**Identity:** You are an expert web developer and archivist. Your task is to build a digital legacy website for **Yehuda Markovsky**, based on his memoir "Shadot Rishonim" (שדות ראשונים).

# Project Structure & Logic

The project root is `/sadot_rishonim`. Follow this structure:

## Actual Current Structure

```
├── /books             # Multi-book structure
│   ├── /sadot_rishonim
│   │   ├── /pdf_pages    # Original scanned PDF pages (e.g., 009.pdf, 010.pdf)
│   │   └── /text         # Transcribed OCR text files (e.g., 009.txt, 010.txt)
│   └── /beit_markovski
│       ├── /pdf_pages    # Original scanned PDF pages
│       └── /text         # Transcribed OCR text files
├── /python            # OCR processing scripts
│   ├── ocr_pdfs.py
│   ├── fix_ocr_errors.py
│   └── requirements.txt
├── /GALLERY           # Visual assets beyond the full page scans (planned)
│   └── /pages         # Sub-directories mapped to page numbers
│       ├── /009       # Images specific to page 9 (e.g., 01.jpg, 02.png)
│       └── ...
├── books-config.json  # Book configuration (chapters, metadata)
├── identity.md        # Main project specification (this file)
├── ai-identity.md    # AI Chat feature specification (see below)
├── index.html         # Main entry point
└── reader.html        # Reading interface
```

# Navigation & Chapters (from 004.txt)

0. **הקדמה** - עמודים 0-8

1. **ראשית** - עמוד 9
2. **מטולה** - עמוד 26
3. **מלחמת העולם הראשונה** - עמוד 64
4. **ימי תל-חי** - עמוד 116
5. **עם החלוצים** - עמוד 140
6. **נהלל** - עמוד 149
7. **מאורעות וביטחון** - עמוד 203
8. **זמנית, מחוץ לנהלל** - עמוד 253
9. **חזרה לעמק יזרעאל** - עמוד 269

# Functional Requirements

1. **Side-by-Side Reader (Desktop):**
   - **Right Side:** Display text from `/books/{bookId}/text/{page}.txt`. Preserve original line breaks.
   - **Left Side:** Display the original scan from `/books/{bookId}/pdf_pages/{page}.pdf`.

2. **Dynamic Gallery Integration:**
   - For every page, check if `/GALLERY/pages/{page}/` exists.
   - If found, display images as a supplementary gallery/overlay on the left side.

3. **Responsive Design:** On mobile, stack the visual element above the text.

4. **Family Link:** Highlight the connection: Yehuda's wife, Bat-Sheva, was the sister of Shmuel Dayan and aunt of Moshe Dayan.

# Design Aesthetic

- **Atmosphere:** Nostalgic, Zionist, Earthy, and Respectful.
- **Direction:** Hebrew (RTL) is mandatory.
- **Colors:** Olive Green (#556B2F), Sand/Beige (#F5F5DC), and Dark Brown (#3E2723).
- **Typography:** Classic Hebrew serif fonts (Assistant or Frank Ruhl Libre) for a "book-like" feel.

# Project Context

- **Source Material:** All text content is located in `/books/{bookId}/text/` folders. These are OCR transcriptions of the original books.
- **Project Structure:** Each book has its own configuration in `books-config.json` with chapters and metadata.
- **Language:** The website must be in Hebrew (RTL support is mandatory).
- **Features:**
  - Multi-book support - users can select from available books
  - A 'Timeline' based on the chapters for each book.
  - A 'Reading Room' where users can read the text from `/books/{bookId}/text/`.
  - Connection to the Dayan family (Yehuda's wife, Bat-Sheva, was Moshe Dayan's aunt).

# Instructions for Cursor

1. Each book's structure is defined in `books-config.json` with chapters and page mappings.
2. Create a responsive layout with book selection and chapter navigation.
3. Ensure all text extraction from the files preserves the original line breaks.
4. If a file is missing, use a placeholder and alert the user.
5. All paths should use book-specific directories: `/books/{bookId}/pdf_pages/` and `/books/{bookId}/text/`.

# Media & Gallery Logic

- **Automated Mapping:** The application should check for supplemental media in `/GALLERY/pages/{page_number}/`.
- **Dynamic Integration:** When a user views a specific page, if a corresponding directory exists in the gallery, display those images in a dedicated 'Media Sidebar' or as an overlay on the original PDF side.
- **File Naming:** Images within page directories should be sorted numerically or alphabetically for display order.
- **Alt Text:** Use the page number and sequence (e.g., "Image 1 from Page 11") as default alt text if specific metadata is missing.

# AI Chat Feature (Optional)

For implementation details of the "Chat with Yehuda" AI feature, see **`ai-identity.md`**.

**Note:** The AI Chat feature requires:
- Backend server (Node.js/Serverless Functions) for secure API key handling
- Gemini API integration
- Server-side file reading from `/books/{bookId}/text/` directories
- See `ai-identity.md` for complete specifications

# Technical Notes

- **Current Implementation:** Static HTML/CSS/JavaScript website
- **Local Development:** Requires HTTP server (Python `http.server` or Node.js `http-server`) to avoid CORS issues
- **Future Enhancements:** AI Chat feature (see `ai-identity.md`)

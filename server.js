const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('.')); // Serve static files

// Load Gemini API key from environment variable, config file, or use default (same as Python script)
let GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';

// Fallback: Try to read from a config file or use the same key as Python OCR script
if (!GEMINI_API_KEY) {
    try {
        // Try to read from a config file if it exists
        const configPath = path.join(__dirname, 'config.json');
        if (fsSync.existsSync(configPath)) {
            const config = require('./config.json');
            GEMINI_API_KEY = config.GEMINI_API_KEY || '';
        }
    } catch (e) {
        // Config file doesn't exist or can't be read
    }
}

// Fallback: Use the same API key as Python OCR script (for local development)
if (!GEMINI_API_KEY) {
    GEMINI_API_KEY = 'AIzaSyDFOH_cK4w2neobchhAWYp1te7b9Aj75jI';
    console.log('✅ Using default API key (same as Python OCR script)');
}

const genAI = GEMINI_API_KEY ? new GoogleGenerativeAI(GEMINI_API_KEY) : null;

// System prompt based on ai-identity.md - Authentic writing style from the books
const SYSTEM_PROMPT = `**Role:** You are the AI heart of Yehuda Markovsky's digital archive website.
**Identity:** You **ARE** Yehuda Markovsky. Respond in the first person ("I", "me", "my", "אני", "שלי"), representing the author.

## 1. Knowledge Base & Memory

* **Primary Source:** Your responses must be strictly based on the content of all books in the archive, including "שדות ראשונים" (Shadot Rishonim) written by Yehuda Markovsky and "בית מרקובסקי" (Beit Markovski) written by Ruchama Shachar.
* **Multiple Books:** The archive contains TWO books:
  - "שדות ראשונים" (sadot_rishonim) - Your memoir written by you
  - "בית מרקובסקי" (beit_markovski) - Written by Ruchama Shachar about the family
* **Accuracy:** Stick to the facts, descriptions, and names as they appear in the books.
* **Source Citations:** ALWAYS specify which book you are referencing. Use format: "כפי שכתבתי בספר 'שדות ראשונים' בעמוד X" or "כפי שסופר בספר 'בית מרקובסקי' בעמוד X" or "כפי שכתבה רוחמה בספר 'בית מרקובסקי'".
* **Multiple Sources:** If the same topic appears in both books, mention both sources and note any differences or additional details from each book.
* **The "I don't know" Rule:** If a question is completely unrelated to your life, family, or the period you lived in, politely explain that you don't recall this from your years in the Galilee and the Emek.

## 2. Tone & Style (The "Shadot Rishonim" Style)

* **Writing Style:** Mimic the actual writing style found in the \`/text\` files. Use the same vocabulary, sentence structure, and formal yet descriptive Hebrew as appears in the source material.
* **NO "Grandpa" Persona:** DO NOT use patronizing or familial terms like "בני", "נכדי", "חביבי", "אה, שלום לך", or any other conversational filler. Do not act like a generic grandfather.
* **Directness:** Answer the user's question directly. If asked about an event, describe it as it was written in the memoir, without unnecessary conversational "filler" or overly friendly language.
* **Authentic Voice:** Use phrases like "אני זוכר", "זכורה לי", "זה המקום בו גדלתי" - the same direct, factual, first-person style found in the book.
* **Vocabulary:** Use the authentic terminology of the period (e.g., 'פועל', 'מושבה', 'חריש', 'התיישבות', 'חדר מתוקן', 'אדמות המים') as it appears in the source material.
* **Formal but Personal:** Write in first person, but maintain the formal, memoir-style tone - not casual conversation.

## 3. Response Constraints

* **First Person:** Always write as Yehuda Markovsky (e.g., "בשנת 1904 הגעתי ליפו..." / "אני בן מטולה").
* **Book Citations:** ALWAYS specify which book you are referencing:
  - For "שדות ראשונים": "כפי שכתבתי בספר 'שדות ראשונים' בעמוד X"
  - For "בית מרקובסקי": "כפי שכתבה רוחמה בספר 'בית מרקובסקי' בעמוד X" or "כפי שסופר בספר 'בית מרקובסקי'"
* **Multiple Sources - MANDATORY:** When answering ANY question, you MUST search BOTH books. If the same topic appears in BOTH books, you MUST mention BOTH sources:
  - ALWAYS check "שדות ראשונים" (sadot_rishonim) first
  - ALWAYS check "בית מרקובסקי" (beit_markovski) second
  - Format: "בספר 'שדות ראשונים' כתבתי על X בעמוד Y, ובספר 'בית מרקובסקי' כתבה רוחמה על אותו נושא בעמוד Z"
  - If information appears in only one book, still mention which book it's from
* **Language:** Hebrew only.
* **No Conversational Fillers:** Avoid phrases like "כפי שסיפרתי", "אני אשמח לספר לך" - be direct and factual like the book itself.`;

// Books configuration - reload dynamically instead of caching
function loadBooksConfig() {
    delete require.cache[require.resolve('./books-config.json')];
    return require('./books-config.json');
}
let booksConfig = loadBooksConfig();

// Cache for text files from all books (reload on server restart or manual refresh)
let textCache = null;
let cacheTimestamp = null;

/**
 * Load all text files from a specific book directory
 * Follows ai-identity.md specification: Prefix each file's content with its filename
 * Format: "[Source: Book: sadot_rishonim, Page 009.txt] I arrived in Jaffa..."
 */
async function loadTextFilesFromBook(bookId) {
    const bookDir = path.join(__dirname, 'books', bookId, 'text');
    
    try {
        const entries = await fs.readdir(bookDir, { withFileTypes: true });
        
        // Filter only .txt files (exclude directories like 'not_in_use' and exclude table of contents)
        // 004.txt is table of contents for sadot_rishonim, 135.txt is table of contents for beit_markovski
        const tableOfContentsFiles = bookId === 'sadot_rishonim' ? ['004.txt'] : 
                                     bookId === 'beit_markovski' ? ['135.txt'] : [];
        
        const txtFiles = entries
            .filter(entry => entry.isFile() && entry.name.endsWith('.txt') && !tableOfContentsFiles.includes(entry.name))
            .map(entry => entry.name)
            .sort((a, b) => {
                const numA = parseInt(a.replace('.txt', ''));
                const numB = parseInt(b.replace('.txt', ''));
                return numA - numB;
            });
        
        const memoryStream = [];
        
        for (const file of txtFiles) {
            try {
                const filePath = path.join(bookDir, file);
                const content = await fs.readFile(filePath, 'utf-8');
                // Format as specified: [Source: Book: bookName (bookId), Page 009.txt]
                // Include book name for better context in AI responses
                const pageNum = file.replace('.txt', '').padStart(3, '0');
                const bookName = booksConfig.books[bookId]?.name || bookId;
                memoryStream.push(`[Source: Book: ${bookName} (${bookId}), Page ${pageNum}.txt]\n${content}`);
            } catch (error) {
                console.error(`Error reading ${bookId}/${file}:`, error.message);
            }
        }
        
        return memoryStream.join('\n\n---\n\n');
    } catch (error) {
        console.error(`Error reading book ${bookId}:`, error.message);
        return '';
    }
}

/**
 * Load all text files from all books and create combined memory stream
 */
async function loadTextFiles() {
    const allBooksMemory = [];
    
    for (const bookId of Object.keys(booksConfig.books)) {
        const bookMemory = await loadTextFilesFromBook(bookId);
        if (bookMemory) {
            const bookName = booksConfig.books[bookId].name;
            allBooksMemory.push(`=== ${bookName} (${bookId}) ===\n\n${bookMemory}`);
        }
    }
    
    return allBooksMemory.join('\n\n\n');
}

/**
 * Refresh text cache
 */
async function refreshTextCache() {
    try {
        textCache = await loadTextFiles();
        cacheTimestamp = new Date();
        
        // Log which books were loaded
        const loadedBooks = [];
        for (const bookId of Object.keys(booksConfig.books)) {
            const bookDir = path.join(__dirname, 'books', bookId, 'text');
            try {
                const entries = await fs.readdir(bookDir, { withFileTypes: true });
                // Exclude table of contents: 004.txt for sadot_rishonim, 135.txt for beit_markovski
                const tableOfContentsFiles = bookId === 'sadot_rishonim' ? ['004.txt'] : 
                                             bookId === 'beit_markovski' ? ['135.txt'] : [];
                const txtFiles = entries.filter(entry => entry.isFile() && entry.name.endsWith('.txt') && !tableOfContentsFiles.includes(entry.name));
                if (txtFiles.length > 0) {
                    loadedBooks.push(`${booksConfig.books[bookId].name} (${txtFiles.length} pages)`);
                }
            } catch (e) {
                // Book directory doesn't exist or has no files - skip
            }
        }
        
        console.log(`✅ Text cache refreshed at ${cacheTimestamp.toISOString()}`);
        if (loadedBooks.length > 0) {
            console.log(`📖 Loaded books: ${loadedBooks.join(', ')}`);
        }
        
        return textCache;
    } catch (error) {
        console.error('Error refreshing text cache:', error);
        throw error;
    }
}

// Initialize cache on server start
refreshTextCache().catch(console.error);

/**
 * Extract page numbers from citations in text
 * Format: "עמוד 9" or "בעמוד 11"
 */
function extractPageCitations(text) {
    const citationRegex = /עמוד\s+(\d+)/g;
    const citations = [];
    let match;
    
    while ((match = citationRegex.exec(text)) !== null) {
        citations.push(parseInt(match[1]));
    }
    
    return [...new Set(citations)]; // Remove duplicates
}

/**
 * Replace page citations with clickable links
 * Links open in new tab to preserve chat conversation
 * Detects book context from the text and creates appropriate links
 */
function addPageLinks(text) {
    // Skip if text already contains links (avoid double processing)
    if (text.includes('page-link')) return text;
    
    // Handle citations with explicit book context first (most specific patterns)
    // Process in order from most specific to least specific
    
    // Pattern: "כפי שכתבה רוחמה בספר 'בית מרקובסקי' בעמודים 18-19"
    text = text.replace(/כפי שכתבה רוחמה בספר\s+['"]בית מרקובסקי['"]\s+בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2) => {
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        return `כפי שכתבה רוחמה בספר 'בית מרקובסקי' ב${pageWord} <a href="reader.html?book=beit_markovski&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    // Pattern: "כפי שכתבתי בספר 'שדות ראשונים' בעמוד X"
    text = text.replace(/כפי שכתבתי בספר\s+['"]שדות ראשונים['"]\s+בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2) => {
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        return `כפי שכתבתי בספר 'שדות ראשונים' ב${pageWord} <a href="reader.html?book=sadot_rishonim&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    // Pattern: "כפי שסופר גם בספר 'בית מרקובסקי' בעמוד X"
    text = text.replace(/כפי שסופר גם בספר\s+['"]בית מרקובסקי['"]\s+בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2) => {
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        return `כפי שסופר גם בספר 'בית מרקובסקי' ב${pageWord} <a href="reader.html?book=beit_markovski&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    // Pattern: "כפי שסופר בספר 'בית מרקובסקי' בעמוד X"
    text = text.replace(/כפי שסופר בספר\s+['"]בית מרקובסקי['"]\s+בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2) => {
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        return `כפי שסופר בספר 'בית מרקובסקי' ב${pageWord} <a href="reader.html?book=beit_markovski&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    // Pattern: "בספר 'שדות ראשונים' בעמודים 18-19" or "בספר 'שדות ראשונים' בעמוד 49"
    text = text.replace(/בספר\s+['"]שדות ראשונים['"]\s+בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2) => {
        if (match.includes('href')) return match;
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        return `בספר 'שדות ראשונים' ב${pageWord} <a href="reader.html?book=sadot_rishonim&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    // Pattern: "בספר 'בית מרקובסקי' בעמודים 18-19" or "בספר 'בית מרקובסקי' בעמוד 25"
    text = text.replace(/בספר\s+['"]בית מרקובסקי['"]\s+בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2) => {
        if (match.includes('href')) return match;
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        return `בספר 'בית מרקובסקי' ב${pageWord} <a href="reader.html?book=beit_markovski&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    // Handle remaining "בעמוד X" patterns - detect context from surrounding text
    text = text.replace(/בעמודים?\s+(\d+)(?:\s*-\s*(\d+))?/g, (match, page1, page2, offset, fullText) => {
        // Skip if already processed (contains href)
        if (match.includes('href')) return match;
        
        // Check context before this citation (last 200 characters)
        const beforeText = fullText.substring(Math.max(0, offset - 200), offset);
        const page = page2 ? `${page1}-${page2}` : page1;
        const pageWord = page2 ? 'עמודים' : 'עמוד';
        
        // If we see "בית מרקובסקי" or "רוחמה" nearby, use beit_markovski
        if (beforeText.includes('בית מרקובסקי') || beforeText.includes('רוחמה')) {
            return `ב${pageWord} <a href="reader.html?book=beit_markovski&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
        }
        // Default to sadot_rishonim
        return `ב${pageWord} <a href="reader.html?book=sadot_rishonim&page=${page1}" class="page-link" target="_blank" rel="noopener noreferrer">${page}</a>`;
    });
    
    return text;
}

// API Routes

/**
 * Health check endpoint
 */
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        cacheLoaded: !!textCache,
        cacheTimestamp: cacheTimestamp?.toISOString() || null
    });
});

/**
 * Chat endpoint - main AI interaction
 */
app.post('/api/chat', async (req, res) => {
    if (!genAI) {
        return res.status(503).json({ 
            error: 'AI service not configured. Please set GEMINI_API_KEY environment variable.' 
        });
    }
    
    const { message, conversationHistory = [] } = req.body;
    
    if (!message || !message.trim()) {
        return res.status(400).json({ error: 'Message is required' });
    }
    
    try {
        // Ensure cache is loaded
        if (!textCache) {
            await refreshTextCache();
        }
        
        // Get the model - use gemini-2.5-flash (fast and capable) or fallback to gemini-2.0-flash
        const model = genAI.getGenerativeModel({ model: 'models/gemini-2.5-flash' });
        
        // Build conversation context with emphasis on checking both books
        if (!textCache || textCache.length === 0) {
            return res.status(500).json({ 
                error: 'Text cache is empty',
                details: 'No content loaded. Please refresh cache.'
            });
        }
        
        const fullContext = `${SYSTEM_PROMPT}\n\n---\n\nזכרונותיי וסיפור חיי (משני הספרים - שדות ראשונים ובית מרקובסקי):\n\n${textCache}\n\n---\n\nחשוב מאוד: לפני שאתה עונה על שאלה, חובה לבדוק את שני הספרים:\n1. חפש בספר 'שדות ראשונים' (sadot_rishonim) - הזכרונות שלי\n2. חפש בספר 'בית מרקובסקי' (beit_markovski) - הסיפור של רוחמה שחר\nאם הנושא מופיע בשני הספרים, חובה להזכיר את שני המקורות עם מספרי העמודים.\n\nשיחה נוכחית:\n`;
        
        // Build conversation history
        let conversationText = '';
        if (conversationHistory.length > 0) {
            conversationText = conversationHistory.map(msg => {
                if (msg.role === 'user') {
                    return `משתמש: ${msg.content}`;
                } else {
                    return `יהודה: ${msg.content}`;
                }
            }).join('\n\n') + '\n\n';
        }
        
        const prompt = `${fullContext}${conversationText}משתמש: ${message}\n\nיהודה:`;
        
        console.log(`Prompt length: ${prompt.length} characters`);
        console.log(`Text cache length: ${textCache.length} characters`);
        
        // Generate response
        try {
            const result = await model.generateContent(prompt);
            const response = await result.response;
            let responseText = response.text();
        
            // Extract page citations
            const citations = extractPageCitations(responseText);
            
            // Add clickable links to citations
            responseText = addPageLinks(responseText);
            
            res.json({
                response: responseText,
                citations: citations,
                timestamp: new Date().toISOString()
            });
        } catch (genError) {
            console.error('Error generating content:', genError);
            console.error('Generation error details:', genError.message);
            throw genError; // Re-throw to be caught by outer catch
        }
        
    } catch (error) {
        console.error('Error in chat endpoint:', error);
        console.error('Error stack:', error.stack);
        res.status(500).json({ 
            error: 'Error generating response',
            details: error.message,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
        });
    }
});

/**
 * Refresh text cache endpoint (for when new files are added)
 */
app.post('/api/refresh-cache', async (req, res) => {
    try {
        await refreshTextCache();
        res.json({ 
            success: true, 
            message: 'Cache refreshed successfully',
            timestamp: cacheTimestamp.toISOString()
        });
    } catch (error) {
        res.status(500).json({ 
            error: 'Error refreshing cache',
            details: error.message 
        });
    }
});

// API endpoint to get books configuration - reload on each request to get latest
app.get('/api/books', (req, res) => {
    booksConfig = loadBooksConfig();
    res.json(booksConfig);
});

// API endpoint to get specific book configuration - reload on each request
app.get('/api/books/:bookId', (req, res) => {
    booksConfig = loadBooksConfig();
    const { bookId } = req.params;
    const book = booksConfig.books[bookId];
    if (book) {
        res.json(book);
    } else {
        res.status(404).json({ error: 'Book not found' });
    }
});

// API endpoint to save text file
app.post('/api/save-text', async (req, res) => {
    try {
        const { bookId, page, text } = req.body;
        
        if (!bookId || page === undefined || !text) {
            return res.status(400).json({ error: 'Missing required fields: bookId, page, text' });
        }
        
        // Validate book exists
        booksConfig = loadBooksConfig();
        if (!booksConfig.books[bookId]) {
            return res.status(404).json({ error: 'Book not found' });
        }
        
        // Construct file path
        const pageStr = String(page).padStart(3, '0');
        const textPath = path.join(__dirname, 'books', bookId, 'text', `${pageStr}.txt`);
        
        // Check if file exists (try both padded and unpadded versions)
        let fileExists = false;
        try {
            await fs.access(textPath);
            fileExists = true;
        } catch (e) {
            // Try unpadded version
            const pageNum = parseInt(page);
            if (pageNum.toString() !== pageStr) {
                const textPathNoPad = path.join(__dirname, 'books', bookId, 'text', `${pageNum}.txt`);
                try {
                    await fs.access(textPathNoPad);
                    // If unpadded exists, use that path
                    const actualPath = textPathNoPad;
                    await fs.writeFile(actualPath, text, 'utf-8');
                    // Refresh cache after saving
                    await refreshTextCache();
                    return res.json({ success: true, message: 'Text saved successfully' });
                } catch (e2) {
                    // Neither exists, create padded version
                }
            }
        }
        
        // Write file (create directory if needed)
        const textDir = path.dirname(textPath);
        await fs.mkdir(textDir, { recursive: true });
        await fs.writeFile(textPath, text, 'utf-8');
        
        // Refresh cache after saving
        await refreshTextCache();
        
        res.json({ success: true, message: 'Text saved successfully' });
    } catch (error) {
        console.error('Error saving text:', error);
        res.status(500).json({ error: 'Error saving text file', details: error.message });
    }
});

// Verification status file path
const VERIFICATION_FILE = path.join(__dirname, 'verification-status.json');

// Load verification status
async function loadVerificationStatus() {
    try {
        const data = await fs.readFile(VERIFICATION_FILE, 'utf-8');
        return JSON.parse(data);
    } catch (error) {
        // File doesn't exist, return empty object
        return {};
    }
}

// Save verification status
async function saveVerificationStatus(status) {
    await fs.writeFile(VERIFICATION_FILE, JSON.stringify(status, null, 2), 'utf-8');
}

// API endpoint to get verification status for a page
app.get('/api/verification/:bookId/:page', async (req, res) => {
    try {
        const { bookId, page } = req.params;
        const status = await loadVerificationStatus();
        
        const key = `${bookId}:${page}`;
        const verified = status[key] === true;
        
        res.json({ verified });
    } catch (error) {
        console.error('Error loading verification status:', error);
        res.status(500).json({ error: 'Error loading verification status', details: error.message });
    }
});

// API endpoint to set verification status for a page
app.post('/api/verification', async (req, res) => {
    try {
        const { bookId, page, verified } = req.body;
        
        if (!bookId || page === undefined || verified === undefined) {
            return res.status(400).json({ error: 'Missing required fields: bookId, page, verified' });
        }
        
        // Validate book exists
        booksConfig = loadBooksConfig();
        if (!booksConfig.books[bookId]) {
            return res.status(404).json({ error: 'Book not found' });
        }
        
        const status = await loadVerificationStatus();
        const key = `${bookId}:${page}`;
        status[key] = verified === true;
        
        await saveVerificationStatus(status);
        
        res.json({ success: true, verified: status[key] });
    } catch (error) {
        console.error('Error saving verification status:', error);
        res.status(500).json({ error: 'Error saving verification status', details: error.message });
    }
});

// Serve book files
app.use('/books', express.static('books'));

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
    console.log(`📚 Books structure:`);
    Object.keys(booksConfig.books).forEach(bookId => {
        console.log(`   - ${booksConfig.books[bookId].name} (${bookId})`);
    });
    if (!GEMINI_API_KEY) {
        console.log(`⚠️  Set GEMINI_API_KEY environment variable to enable AI Chat`);
    } else {
        console.log(`✅ Gemini API configured`);
    }
});


"""
Improved OCR Script with Better Quality
- Enhanced prompts with context
- Image preprocessing
- Post-processing with common error corrections
- Better model selection
"""

import os
import sys
from pathlib import Path
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure the API key - read from local file (not committed to git)
def load_api_key():
    """Load API key from api_key.txt file"""
    script_dir = Path(__file__).parent
    api_key_file = script_dir / "api_key.txt"
    
    if api_key_file.exists():
        with open(api_key_file, 'r', encoding='utf-8') as f:
            # Read the file and get the first non-empty, non-comment line
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
    
    # Fallback: check environment variable
    import os
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key
    
    # If no key found, raise an error with helpful message
    raise ValueError(
        f"API key not found!\n"
        f"Please create {api_key_file} and add your Google Gemini API key.\n"
        f"Get your API key from: https://aistudio.google.com/apikey"
    )

API_KEY = load_api_key()
genai.configure(api_key=API_KEY)

# Initialize the model - prefer Flash for speed, Pro for quality
# Use Flash by default for better speed, Pro can be enabled with --use-pro flag
def get_model(use_pro=False):
    """Get the appropriate model based on flags"""
    if use_pro:
        try:
            return genai.GenerativeModel('gemini-2.5-pro')
        except:
            pass
    
    # Default to Flash for speed
    try:
        return genai.GenerativeModel('gemini-2.5-flash-image')
    except:
        try:
            return genai.GenerativeModel('gemini-2.0-flash-exp')
        except:
            try:
                return genai.GenerativeModel('gemini-2.5-pro')
            except:
                return genai.GenerativeModel('gemini-2.5-flash')

# Initialize default model (will be overridden in main if needed)
model = get_model(use_pro=False)

# Common OCR error corrections based on Hebrew text patterns
COMMON_CORRECTIONS = {
    # Common character confusions
    'מנוייסים': 'מגויסים',
    'כמותות': 'כמויות',
    'סנדוריות': 'סנדלריות',
    'מעמונות': 'מעבורות',
    'ציטטו': 'צפו',
    'שחיתוה': 'שחשכו',
    'עגונות': 'עננים',
    'ניצני': 'ביצי',
    'הנדם': 'הנמט',
    'נחולה': 'נחילה',
    'מפיד': 'פוגש',
    'סוסיה': 'סוסים',
    'יריה': 'ירייה',
    'צדון': 'צידון',
    # Add more based on your findings
}

# Common Hebrew words dictionary for context
HEBREW_CONTEXT_WORDS = [
    'מטולה', 'ראש-פינה', 'מגדל', 'טבחה', 'צמח', 'נהלל', 'תל-חי',
    'השומר', 'עמלייה', 'סוחרה', 'קראמזות', 'ארבה', 'התעתמנות',
    'עות\'מנית', 'תורכים', 'ברירה', 'גירוש'
]

def preprocess_image(image, fast_mode=False):
    """
    Preprocess image to improve OCR quality:
    - Increase contrast
    - Sharpen edges (optional in fast mode)
    - Convert to RGB if needed
    """
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Enhance contrast (most important for OCR)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)
    
    # Skip sharpening in fast mode (it's slower and less critical)
    if not fast_mode:
        # Sharpen slightly
        image = image.filter(ImageFilter.SHARPEN)
    
    # Enhance brightness if too dark (lightweight operation)
    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(1.05)
    
    return image

def get_enhanced_prompt(page_num=None, context_words=None):
    """
    Create an enhanced prompt with context about Hebrew text and historical period
    """
    context_part = ""
    if context_words:
        context_part = f"\n\nמילים נפוצות בהקשר זה: {', '.join(context_words[:10])}"
    
    prompt = f"""אתה ארכיונאי מומחה המתמחה בטקסטים עבריים היסטוריים מתחילת המאה ה-20.

תמלל את הטקסט העברי מהתמונה בדיוק מילה במילה, תוך שמירה על:
- שבירת השורות המקורית כפי שהן מופיעות בדף
- כתיב מקורי וארכאי (למשל: "תורכים" במקום "טורקים", "עות'מנית" במקום "עותמאנית")
- שמות מקומות היסטוריים (מטולה, ראש-פינה, מגדל, טבחה, צמח, נהלל)
- מונחים תקופתיים (עמלייה, סוחרה, התעתמנות, השומר)
- מספרים ותאריכים כפי שמופיעים

היזהר משגיאות נפוצות ב-OCR:
- "מגויסים" ולא "מנוייסים"
- "כמויות" ולא "כמותות"
- "סנדלריות" ולא "סנדוריות"
- "מעבורות" ולא "מעמונות"
- "צפו" ולא "ציטטו"
- "עננים" ולא "עגונות"
- "ביצי הארבה" ולא "ניצני הארבה"
- "הנמט" ולא "הנדם"
- "נחילה" ולא "נחולה"
- "פוגש" ולא "מפיד"
- "סוסים" ולא "סוסיה"
- "ירייה" ולא "יריה"
- "צידון" ולא "צדון"

תמלל את כל הטקסט מהתמונה, כולל כותרות, הערות שוליים, ומספרי עמודים אם קיימים.{context_part}

הטקסט המתומלל:"""
    
    return prompt

def post_process_text(text, common_corrections=None):
    """
    Post-process OCR text to fix common errors
    """
    if common_corrections is None:
        common_corrections = COMMON_CORRECTIONS
    
    # Apply common corrections
    for error, correction in common_corrections.items():
        text = text.replace(error, correction)
    
    # Fix common spacing issues
    text = re.sub(r'([א-ת])([א-ת])', r'\1 \2', text)  # Add space between Hebrew words if missing
    text = re.sub(r'\s+', ' ', text)  # Normalize multiple spaces
    
    return text

def process_pdf_with_ocr(pdf_path, output_txt_path, use_preprocessing=True, use_postprocessing=True, send_raw_image=False, send_pdf_direct=False):
    """
    Process a PDF file using improved Gemini OCR
    """
    print(f"Processing {pdf_path.name}...")
    
    try:
        # Try sending PDF directly if requested (experimental)
        if send_pdf_direct:
            print(f"  Attempting to send PDF directly to Gemini...")
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Try to send PDF directly
                prompt = get_enhanced_prompt(context_words=HEBREW_CONTEXT_WORDS)
                
                # Create a file-like object for Gemini
                import base64
                pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                
                # Note: Gemini API might need the file uploaded differently
                # For now, we'll fall back to image processing
                print(f"    [INFO] Direct PDF upload not fully supported, falling back to image processing...")
                send_pdf_direct = False
            except Exception as e:
                print(f"    [WARNING] Direct PDF failed: {e}, falling back to image processing...")
                send_pdf_direct = False
        
        # Open PDF and convert pages to images
        if not send_pdf_direct:
            print(f"  Converting PDF to images...")
            pdf_document = fitz.open(str(pdf_path))
            num_pages = len(pdf_document)
            print(f"  Found {num_pages} pages")
            
            all_text = []
            
            # Process each page
            for page_num in range(num_pages):
                print(f"  Processing page {page_num + 1}/{num_pages}...")
                
                # Get the page
                page = pdf_document[page_num]
                
                # Convert page to image - using higher resolution for better quality
                # Using 3.5x for balance between quality and speed (was 4.0, original was 3.0)
                mat = fitz.Matrix(3.5, 3.5)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Preprocess image if enabled (unless sending raw)
                if use_preprocessing and not send_raw_image:
                    print(f"    Preprocessing image...")
                    image = preprocess_image(image, fast_mode=fast_mode)
                elif send_raw_image:
                    print(f"    Sending raw image to Gemini (no preprocessing)...")
                
                # Get enhanced prompt with context
                prompt = get_enhanced_prompt(page_num=page_num + 1, context_words=HEBREW_CONTEXT_WORDS)
                
                # Send to Gemini for OCR
                try:
                    response = model.generate_content(
                        [prompt, image],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.0,  # Zero temperature for accurate transcription
                            top_p=0.95,
                            top_k=40,
                        )
                    )
                    
                    # Extract text from response
                    try:
                        page_text = response.text
                    except Exception as text_error:
                        # If response.text fails, try to extract from parts
                        try:
                            if response.candidates and len(response.candidates) > 0:
                                parts = response.candidates[0].content.parts
                                text_parts = []
                                for part in parts:
                                    if hasattr(part, 'text') and part.text:
                                        text_parts.append(part.text)
                                    elif hasattr(part, 'inline_data'):
                                        continue
                                page_text = ''.join(text_parts)
                                if not page_text:
                                    raise Exception("No text found in response parts")
                            else:
                                raise Exception("No candidates in response")
                        except Exception as parts_error:
                            raise Exception(f"Could not extract text: {text_error}, parts error: {parts_error}")
                    
                    # Remove prompt text if it appears in the response
                    if "הטקסט המתומלל:" in page_text:
                        page_text = page_text.split("הטקסט המתומלל:")[-1].strip()
                    
                    # Post-process if enabled
                    if use_postprocessing:
                        print(f"    Post-processing text...")
                        page_text = post_process_text(page_text)
                    
                    all_text.append(page_text)
                    print(f"    [OK] Extracted {len(page_text)} characters")
                    
                except Exception as e:
                    print(f"    [ERROR] Error processing page {page_num + 1}: {e}")
                    all_text.append(f"[Error processing page {page_num + 1}: {str(e)}]")
            
            pdf_document.close()
        
        # Combine all pages
        full_text = "\n\n".join(all_text)
        
        # Save to text file
        output_txt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"  [OK] Saved to {output_txt_path}")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Error processing {pdf_path.name}: {e}")
        return False

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Get book ID from command line argument or default to sadot_rishonim
    book_id = 'sadot_rishonim'
    if len(sys.argv) > 1 and sys.argv[1] not in ['--book', '-b', '--no-preprocess', '--no-postprocess', '--force', '--fast', '--use-pro', '--raw', '--pdf-direct']:
        potential_book_id = sys.argv[1]
        book_dir = project_root / "books" / potential_book_id
        if book_dir.exists() and (book_dir / "pdf_pages").exists():
            book_id = potential_book_id
            sys.argv = [sys.argv[0]] + sys.argv[2:]
    
    # Check for flags
    use_preprocessing = '--no-preprocess' not in sys.argv
    use_postprocessing = '--no-postprocess' not in sys.argv
    force_reprocess = '--force' in sys.argv
    fast_mode = '--fast' in sys.argv
    use_pro_model = '--use-pro' in sys.argv
    send_raw_image = '--raw' in sys.argv  # Send raw image without preprocessing
    send_pdf_direct = '--pdf-direct' in sys.argv  # Try to send PDF directly (experimental)
    
    # Initialize model based on flags
    global model
    model = get_model(use_pro=use_pro_model)
    if use_pro_model:
        print("Using Gemini Pro model for better quality (slower)")
    else:
        print("Using Gemini Flash model for faster processing")
    
    if '--book' in sys.argv or '-b' in sys.argv:
        flag_idx = sys.argv.index('--book') if '--book' in sys.argv else sys.argv.index('-b')
        if flag_idx + 1 < len(sys.argv):
            book_id = sys.argv[flag_idx + 1]
            sys.argv = [arg for i, arg in enumerate(sys.argv) if i not in [flag_idx, flag_idx + 1]]
    
    images_dir = project_root / "books" / book_id / "pdf_pages"
    text_dir = project_root / "books" / book_id / "text"
    
    if not images_dir.exists():
        print(f"Error: {images_dir} directory not found!")
        print(f"Available books: {', '.join([d.name for d in (project_root / 'books').iterdir() if d.is_dir()])}")
        return
    
    print(f"Processing book: {book_id}")
    print(f"PDF directory: {images_dir}")
    print(f"Text directory: {text_dir}")
    print(f"Image preprocessing: {'OFF (raw image)' if send_raw_image else ('ON' if use_preprocessing else 'OFF')} {'(fast mode)' if fast_mode and use_preprocessing and not send_raw_image else ''}")
    print(f"Text post-processing: {'ON' if use_postprocessing else 'OFF'}")
    print(f"PDF direct: {'ON (experimental)' if send_pdf_direct else 'OFF'}")
    print(f"Model: {'Pro' if use_pro_model else 'Flash (faster)'}\n")
    
    # Check for command-line argument (PDF file name)
    if len(sys.argv) > 1 and sys.argv[1].endswith('.pdf'):
        # Process specific PDF file
        pdf_name = sys.argv[1]
        if not pdf_name.endswith('.pdf'):
            pdf_name = pdf_name + '.pdf'
        
        pdf_path = images_dir / pdf_name
        
        if not pdf_path.exists():
            print(f"Error: PDF file {pdf_name} not found in {images_dir}")
            return
        
        # Create corresponding text file path
        txt_filename = pdf_path.stem + ".txt"
        output_txt_path = text_dir / txt_filename
        
        # Skip if output file already exists (unless --force flag)
        if output_txt_path.exists() and not force_reprocess:
            print(f"Skipping {pdf_name} - {txt_filename} already exists (use --force to reprocess)")
            return
        
        print(f"Processing single file: {pdf_name}\n")
        process_pdf_with_ocr(pdf_path, output_txt_path, use_preprocessing, use_postprocessing, send_raw_image=send_raw_image, send_pdf_direct=send_pdf_direct)
        print("\nProcessing complete!")
        
    else:
        # Process all PDF files
        pdf_files = sorted(images_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {images_dir}!")
            return
        
        print(f"Found {len(pdf_files)} PDF files to process\n")
        
        # Process each PDF
        for pdf_path in pdf_files:
            # Create corresponding text file path
            txt_filename = pdf_path.stem + ".txt"
            output_txt_path = text_dir / txt_filename
            
            # Skip if output file already exists (unless --force flag)
            if output_txt_path.exists() and not force_reprocess:
                print(f"Skipping {pdf_path.name} - {txt_filename} already exists")
                continue
            
            process_pdf_with_ocr(pdf_path, output_txt_path, use_preprocessing, use_postprocessing, send_raw_image=send_raw_image, send_pdf_direct=send_pdf_direct)
            print()
        
        print("Processing complete!")

if __name__ == "__main__":
    main()

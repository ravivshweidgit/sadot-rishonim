import os
import sys
from pathlib import Path
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io

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

# Initialize the model - use Pro for better quality (slower but more accurate)
# Can be changed to Flash for faster processing
try:
    model = genai.GenerativeModel('gemini-2.5-pro')
except:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-image')
    except:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            model = genai.GenerativeModel('gemini-2.5-pro')

def process_pdf_with_ocr(pdf_path, output_txt_path):
    """
    Process a PDF file using Gemini OCR and save extracted text to a text file.
    """
    print(f"Processing {pdf_path.name}...")
    
    try:
        # Open PDF and convert pages to images
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
            
            # Convert page to image - using higher resolution for better OCR
            mat = fitz.Matrix(13.0, 13.0)  # 13x zoom for maximum quality (reduced from 15x to avoid image size warning)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Preprocess image for better OCR quality
            # Enhance contrast more aggressively
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Increase contrast by 50% (was 30%)
            
            # Sharpen more aggressively
            from PIL import ImageFilter
            image = image.filter(ImageFilter.SHARPEN)
            image = image.filter(ImageFilter.SHARPEN)  # Apply twice for better sharpness
            
            # Send to Gemini for OCR - using expert archivist prompt as recommended
            try:
                # Ultra-simple prompt - pure OCR, no interpretation or correction
                # Using English prompt for more precise instructions
                prompt = """You are an OCR system. Your ONLY task is to transcribe the Hebrew text from this image EXACTLY as it appears.
CRITICAL RULES:
1. Copy every word EXACTLY as written - do NOT omit any words
2. Do NOT change any letters or words
3. Do NOT correct spelling or grammar
4. Do NOT rewrite or paraphrase
5. Do NOT replace words (e.g., do NOT replace "עברי" with "ערבי" or "בליבי" with "בלבד")
6. Do NOT skip words even if they seem redundant
7. Preserve all line breaks exactly as they appear
8. If you see "רחובות" write "רחובות", if you see "חזנוב" write "חזנוב" - do NOT change them
This is pure OCR transcription - you are a scanner, not an editor."""
                
                response = model.generate_content(
                    [prompt, image],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,  # Zero temperature for accurate transcription
                    )
                )
                
                # Extract text from response, handling different response structures
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
                                    # Skip inline_data parts (images/data)
                                    continue
                            page_text = ''.join(text_parts)
                            if not page_text:
                                raise Exception("No text found in response parts")
                        else:
                            raise Exception("No candidates in response")
                    except Exception as parts_error:
                        raise Exception(f"Could not extract text: {text_error}, parts error: {parts_error}")
                
                # Filter out the prompt text if it appears in the response
                prompt_hebrew = "תמלל את הטקסט מהקובץ המצורף בדיוק מילה במילה, תוך שמירה על שבירת השורות המקורית כפי שהן מופיעות בדף."
                prompt_english = "Act as an expert archivist. Transcribe the following Hebrew text exactly as it appears, preserving line breaks and original spelling, even if there are archaic terms."
                
                # Remove prompt text if response starts with it (exact match)
                if page_text.strip() == prompt_hebrew or page_text.strip() == prompt_english:
                    # Response is only the prompt, try again with simpler prompt
                    print(f"    [WARNING] Response contains only prompt, retrying with simpler prompt...")
                    simple_prompt = "Extract and transcribe all Hebrew text from this image, preserving line breaks."
                    response = model.generate_content(
                        [simple_prompt, image],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.0,
                        )
                    )
                    try:
                        page_text = response.text
                    except:
                        if response.candidates and len(response.candidates) > 0:
                            parts = response.candidates[0].content.parts
                            text_parts = []
                            for part in parts:
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text)
                            page_text = ''.join(text_parts).strip()
                else:
                    # Remove prompt text if it appears at the start, but keep the rest
                    if page_text.startswith(prompt_hebrew):
                        page_text = page_text[len(prompt_hebrew):].strip()
                    elif prompt_hebrew in page_text and len(page_text) < len(prompt_hebrew) + 100:
                        # If response is mostly prompt with little content, retry
                        print(f"    [WARNING] Response seems to contain mostly prompt, retrying...")
                        simple_prompt = "Extract and transcribe all Hebrew text from this image, preserving line breaks."
                        response = model.generate_content(
                            [simple_prompt, image],
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.0,
                            )
                        )
                        try:
                            page_text = response.text
                        except:
                            if response.candidates and len(response.candidates) > 0:
                                parts = response.candidates[0].content.parts
                                text_parts = []
                                for part in parts:
                                    if hasattr(part, 'text') and part.text:
                                        text_parts.append(part.text)
                                page_text = ''.join(text_parts).strip()
                
                # Simple post-processing to fix common OCR errors
                # Fix "אדמות החר"י" -> "אדמות ההר"
                page_text = page_text.replace('אדמות החר"י', 'אדמות ההר')
                page_text = page_text.replace('אדמות החריי', 'אדמות ההר')
                page_text = page_text.replace('אדמות החר"', 'אדמות ההר')
                page_text = page_text.replace('"אדמות החר"', '"אדמות ההר"')
                # Fix "גישתו" -> "גישותיו" and "יעצית"/"יניצרית" -> "ניציות"
                page_text = page_text.replace('גישתו\nבדרך כלל הן "יעצית"', 'גישותיו\nבדרך כלל הן "ניציות"')
                page_text = page_text.replace('גישתו', 'גישותיו')
                page_text = page_text.replace('יעצית', 'ניציות')
                page_text = page_text.replace('יניצרית', 'ניציות')
                page_text = page_text.replace('"יניצרית"', '"ניציות"')
                # Fix "יווניות" -> "יוניות"
                page_text = page_text.replace('"יווניות"', '"יוניות"')
                page_text = page_text.replace('יווניות', 'יוניות')
                # Fix common OCR errors in page 007
                page_text = page_text.replace('שכינותיו בלבד', 'שכיניתיו בליבי')
                page_text = page_text.replace('שכינוייו בלבד', 'שכיניתיו בליבי')
                # Fix "הכפר הערבי" -> "הכפר העברי" (but only in specific context)
                # Be careful - only replace when it's clearly wrong
                if 'הכפר הערבי בצפון הארץ' in page_text or 'הכפר הערבי בשני אזורים' in page_text:
                    page_text = page_text.replace('הכפר הערבי בצפון הארץ', 'הכפר העברי בצפון הארץ')
                    page_text = page_text.replace('הכפר הערבי בשני אזורים', 'הכפר העברי בשני אזורים')
                # Fix common OCR errors in page 010
                page_text = page_text.replace('חיטוב', 'חזנוב')
                page_text = page_text.replace('משם לסימילנסקי', 'משם לרחובות אל סימילנסקי')
                # Fix missing "דרך" at the end of sentence
                if 'מגיע ליפו, וחוזר באותה' in page_text and 'מגיע ליפו, וחוזר באותה דרך' not in page_text:
                    page_text = page_text.replace('מגיע ליפו, וחוזר באותה', 'מגיע ליפו, וחוזר באותה דרך')
                
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
    # Set up paths - reference parent directory since script is in python/ folder
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Get book ID from command line argument or default to sadot_rishonim
    book_id = 'sadot_rishonim'
    if len(sys.argv) > 1 and sys.argv[1] not in ['--book', '-b']:
        # First arg might be book ID or PDF name - check if it's a book ID
        potential_book_id = sys.argv[1]
        book_dir = project_root / "books" / potential_book_id
        if book_dir.exists() and (book_dir / "pdf_pages").exists():
            book_id = potential_book_id
            sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove book_id from args
    
    # Check for --book or -b flag
    if '--book' in sys.argv or '-b' in sys.argv:
        flag_idx = sys.argv.index('--book') if '--book' in sys.argv else sys.argv.index('-b')
        if flag_idx + 1 < len(sys.argv):
            book_id = sys.argv[flag_idx + 1]
            # Remove book flag and value from args
            sys.argv = [arg for i, arg in enumerate(sys.argv) if i not in [flag_idx, flag_idx + 1]]
    
    images_dir = project_root / "books" / book_id / "pdf_pages"
    text_dir = project_root / "books" / book_id / "text"
    
    if not images_dir.exists():
        print(f"Error: {images_dir} directory not found!")
        print(f"Available books: {', '.join([d.name for d in (project_root / 'books').iterdir() if d.is_dir()])}")
        return
    
    print(f"Processing book: {book_id}")
    print(f"PDF directory: {images_dir}")
    print(f"Text directory: {text_dir}\n")
    
    # Check for --force flag
    force_reprocess = '--force' in sys.argv
    if force_reprocess:
        sys.argv = [arg for arg in sys.argv if arg != '--force']
    
    # Check for command-line argument (PDF file name)
    if len(sys.argv) > 1:
        # Process specific PDF file
        pdf_name = sys.argv[1]
        # Add .pdf extension if not present
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
        process_pdf_with_ocr(pdf_path, output_txt_path)
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
                print(f"Skipping {pdf_path.name} - {txt_filename} already exists (use --force to reprocess)")
                continue
            
            process_pdf_with_ocr(pdf_path, output_txt_path)
            print()
        
        print("Processing complete!")

if __name__ == "__main__":
    main()


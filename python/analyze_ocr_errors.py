"""
Analyze OCR errors and build a correction dictionary
This script helps identify common OCR errors by analyzing existing corrections
and suggesting improvements
"""

from pathlib import Path
import json
import re
from collections import Counter
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_existing_corrections(corrections_file="python/ocr_corrections.json"):
    """Load existing corrections from file"""
    script_dir = Path(__file__).parent
    corrections_path = script_dir / corrections_file if not Path(corrections_file).is_absolute() else Path(corrections_file)
    
    if corrections_path.exists():
        with open(corrections_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def analyze_text_file(text_file):
    """Analyze a text file for potential OCR errors"""
    potential_errors = []
    
    # Common Hebrew OCR error patterns
    error_patterns = [
        (r'מנוייסים', 'מגויסים'),
        (r'כמותות', 'כמויות'),
        (r'סנדוריות', 'סנדלריות'),
        (r'מעמונות', 'מעבורות'),
        (r'ציטטו', 'צפו'),
        (r'שחיתוה', 'שחשכו'),
        (r'עגונות', 'עננים'),
        (r'ניצני הארבה', 'ביצי הארבה'),
        (r'הנדם', 'הנמט'),
        (r'נחולה', 'נחילה'),
        (r'מפיד', 'פוגש'),
        (r'סוסיה', 'סוסים'),
        (r'יריה\b', 'ירייה'),
        (r'צדון', 'צידון'),
        # Add more patterns as you discover them
    ]
    
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, correction in error_patterns:
                    if re.search(pattern, line):
                        potential_errors.append({
                            'file': text_file.name,
                            'line': line_num,
                            'pattern': pattern,
                            'suggested_correction': correction,
                            'context': line.strip()[:100]  # First 100 chars for context
                        })
    except Exception as e:
        print(f"Error reading {text_file}: {e}")
    
    return potential_errors

def build_correction_dictionary(text_dir, output_file="python/ocr_corrections_auto.json"):
    """Build a dictionary of common OCR errors from text files"""
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file if not Path(output_file).is_absolute() else Path(output_file)
    
    all_errors = []
    text_files = list(text_dir.glob("*.txt"))
    
    print(f"Analyzing {len(text_files)} text files...")
    
    for text_file in text_files:
        errors = analyze_text_file(text_file)
        all_errors.extend(errors)
    
    # Count frequency of each error pattern
    error_counts = Counter([e['pattern'] for e in all_errors])
    
    # Build correction dictionary
    corrections = {}
    for error in all_errors:
        pattern = error['pattern']
        correction = error['suggested_correction']
        
        if pattern not in corrections:
            corrections[pattern] = {
                'correction': correction,
                'count': error_counts[pattern],
                'files': set()
            }
        corrections[pattern]['files'].add(error['file'])
    
    # Convert sets to lists for JSON serialization
    for pattern in corrections:
        corrections[pattern]['files'] = list(corrections[pattern]['files'])
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)
    
    print(f"\nFound {len(corrections)} unique error patterns:")
    for pattern, info in sorted(corrections.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"  {pattern} → {info['correction']} ({info['count']} occurrences in {len(info['files'])} files)")
    
    print(f"\nCorrections saved to {output_path}")
    return corrections

def suggest_improvements(text_dir):
    """Suggest improvements based on common patterns"""
    print("Analyzing text files for OCR error patterns...\n")
    
    corrections = build_correction_dictionary(text_dir)
    
    print("\n" + "="*60)
    print("SUGGESTIONS FOR IMPROVING OCR QUALITY:")
    print("="*60)
    
    print("\n1. Add these patterns to COMMON_CORRECTIONS in ocr_pdfs_improved.py:")
    for pattern, info in sorted(corrections.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f'    "{pattern}": "{info["correction"]}",  # Found {info["count"]} times')
    
    print("\n2. Consider adding these to the enhanced prompt:")
    print("   - Common error patterns that appear frequently")
    print("   - Context-specific words from the analyzed files")
    
    return corrections

def main():
    import sys
    
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Get book ID from command line argument or default to sadot_rishonim
    book_id = 'sadot_rishonim'
    if len(sys.argv) > 1 and sys.argv[1] not in ['--book', '-b']:
        potential_book_id = sys.argv[1]
        book_dir = project_root / "books" / potential_book_id
        if book_dir.exists() and (book_dir / "text").exists():
            book_id = potential_book_id
            sys.argv = [sys.argv[0]] + sys.argv[2:]
    
    if '--book' in sys.argv or '-b' in sys.argv:
        flag_idx = sys.argv.index('--book') if '--book' in sys.argv else sys.argv.index('-b')
        if flag_idx + 1 < len(sys.argv):
            book_id = sys.argv[flag_idx + 1]
    
    text_dir = project_root / "books" / book_id / "text"
    
    if not text_dir.exists():
        print(f"Error: {text_dir} directory not found!")
        print(f"Available books: {', '.join([d.name for d in (project_root / 'books').iterdir() if d.is_dir()])}")
        return
    
    print(f"Analyzing OCR errors in book: {book_id}")
    print(f"Text directory: {text_dir}\n")
    
    suggest_improvements(text_dir)

if __name__ == "__main__":
    main()

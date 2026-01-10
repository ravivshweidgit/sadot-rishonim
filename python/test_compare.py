"""Test comparison function"""
import sys
sys.path.insert(0, 'python')
from add_niqqud import compare_texts, remove_niqqud
import unicodedata

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Read original
with open('books/beit_markovski/text/000.txt', 'r', encoding='utf-8') as f:
    original = f.read()

# Simulate what the API returns
niqqud_text = 'בַּיִת\nמַרְקוֹבְסְקִי\n\nרוּחָמָה שַׁחַר'

print("Original:")
print(repr(original))
print("\nNiqqud:")
print(repr(niqqud_text))
print("\n" + "="*50 + "\n")

# Compare
match, differences = compare_texts(original, niqqud_text)

print(f"Match: {match}")
print(f"Differences: {len(differences)}")

if differences:
    print("\nDifferences found:")
    for diff in differences:
        print(f"  Line {diff['line']}:")
        print(f"    Original: {repr(diff['original'])}")
        print(f"    Niqqud:   {repr(diff['niqqud'])}")

# Also check manually
original_no_niqqud = remove_niqqud(original)
niqqud_no_niqqud = remove_niqqud(niqqud_text)

print("\n" + "="*50)
print("Manual comparison:")
print(f"Original (no niqqud): {repr(original_no_niqqud)}")
print(f"Niqqud (no niqqud):   {repr(niqqud_no_niqqud)}")
print(f"Match: {original_no_niqqud == niqqud_no_niqqud}")

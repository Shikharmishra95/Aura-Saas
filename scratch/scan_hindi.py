import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

HINDI_PATTERN = re.compile(r'[\u0900-\u097F]')

def extract_hindi_strings(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    
    results = []
    
    # Match JSX text content: >...Hindi...<
    jsx_text = re.findall(r'>\s*([^<>{}\n]{2,80})\s*<', content)
    for s in jsx_text:
        s = s.strip()
        if HINDI_PATTERN.search(s) and len(s) > 1:
            results.append(s)
    
    # Match string literals in JS: '...Hindi...' or "...Hindi..."
    string_lits = re.findall(r'[\'"]([^\'"<>{}\n]{2,80})[\'"]', content)
    for s in string_lits:
        s = s.strip()
        if HINDI_PATTERN.search(s) and len(s) > 1:
            results.append(s)
    
    # Match template literals with Hindi
    tmpl = re.findall(r'`([^`\n]{2,80})`', content)
    for s in tmpl:
        s = s.strip()
        if HINDI_PATTERN.search(s) and len(s) > 1 and '$' not in s:
            results.append(s)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for s in results:
        cleaned = re.sub(r'\s+', ' ', s).strip()
        if cleaned not in seen and len(cleaned) > 1:
            seen.add(cleaned)
            unique.append(cleaned)
    
    return unique

files = [
    r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx',
    r'c:\Users\shiva\Desktop\AAA\frontend\src\PatientPortal.jsx'
]

all_strings = []
for f in files:
    strings = extract_hindi_strings(f)
    all_strings.extend(strings)

# Deduplicate across files
seen = set()
final = []
for s in all_strings:
    if s not in seen:
        seen.add(s)
        final.append(s)

print(f"Total unique Hindi strings found: {len(final)}\n")
print("=" * 60)
for i, s in enumerate(final, 1):
    print(f"{i:3}. {s}")

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in App.jsx: {len(lines)}")

# Count matching curly braces and JSX parens
open_braces = 0
close_braces = 0
for i, l in enumerate(lines, 1):
    open_braces += l.count('{')
    close_braces += l.count('}')

print(f"Open braces {{: {open_braces}, Close braces }}: {close_braces}")

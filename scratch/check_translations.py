import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'frontend/src/App.jsx', encoding='utf-8') as f:
    lines = f.readlines()

print('Checking TRANSLATIONS block (lines 1-285) for bad t() calls:')
found = False
for i, line in enumerate(lines[:285], 1):
    stripped = line.strip()
    if stripped.startswith('//'):
        continue
    if "t('" in stripped or 't("' in stripped:
        print(f'LINE {i}: {line.rstrip()}')
        found = True

if not found:
    print('All clean! No bad t() calls found in TRANSLATIONS block.')

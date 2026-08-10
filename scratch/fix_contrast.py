import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace hardcoded dark-mode white text styles with high contrast CSS variables
replacements = [
    ("color: '#fff'", "color: 'var(--text-main)'"),
    ('color: "#fff"', 'color: "var(--text-main)"'),
    ("color: '#ffffff'", "color: 'var(--text-main)'"),
    ('color: "#ffffff"', 'color: "var(--text-main)"'),
    ("color: 'white'", "color: 'var(--text-main)'"),
    ('color: "white"', 'color: "var(--text-main)"'),
    ("color: '#ccc'", "color: 'var(--text-secondary)'"),
    ('color: "#ccc"', 'color: "var(--text-secondary)"'),
    ("background: 'rgba(255,255,255,0.04)'", "background: '#FFFFFF'"),
    ("background: 'rgba(255,255,255,0.03)'", "background: '#FFFFFF'"),
    ("background: 'rgba(255,255,255,0.02)'", "background: '#FFFFFF'"),
    ("background: 'rgba(255,255,255,0.05)'", "background: 'var(--bg-muted)'"),
    ("background: 'rgba(0,0,0,0.2)'", "background: 'var(--bg-muted)'"),
    ("border: '1px solid rgba(255,255,255,0.08)'", "border: '1px solid var(--border)'"),
    ("border: '1px solid rgba(255,255,255,0.1)'", "border: '1px solid var(--border)'"),
    ("border: '1px solid rgba(255,255,255,0.15)'", "border: '1px solid var(--border)'"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx inline text contrast fix completed.")

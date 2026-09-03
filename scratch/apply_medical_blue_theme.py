import re

index_css_path = r'c:\Users\shiva\Desktop\AAA\frontend\src\index.css'
app_css_path = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.css'

# 1. Update index.css design tokens
with open(index_css_path, 'r', encoding='utf-8') as f:
    index_css = f.read()

index_css = index_css.replace('--bg-main: #F0F4FA;', '--bg-main: #F0F4FA;')
index_css = index_css.replace('--primary: #2563EB;', '--primary: #2563EB;')
index_css = index_css.replace('--primary-hover: #1D4ED8;', '--primary-hover: #1D4ED8;')
index_css = index_css.replace('--primary-soft: #EFF6FF;', '--primary-soft: #EFF6FF;')
index_css = index_css.replace('--primary-border: #BFDBFE;', '--primary-border: #BFDBFE;')

# Ensure input styling has rounded square borders (8px) and rich blue focus rings
if '.btn-primary' not in index_css:
    index_css += '''

/* Medical Hospital Blue Theme Additions */
.btn-primary {
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25) !important;
  transition: all 0.2s ease !important;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35) !important;
  transform: translateY(-1px);
}

input:focus, select:focus, textarea:focus {
  border-color: #2563EB !important;
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
}
'''

with open(index_css_path, 'w', encoding='utf-8') as f:
    f.write(index_css)

# 2. Update App.css table header and card styles
with open(app_css_path, 'r', encoding='utf-8') as f:
    app_css = f.read()

# Enhance table header ice blue background
table_th_replacement = '''
.custom-table th {
  background: #EFF6FF !important;
  color: #1E40AF !important;
  font-weight: 800 !important;
  font-size: 12px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
  padding: 14px 16px !important;
  border-bottom: 2px solid #BFDBFE !important;
}
'''

if '.custom-table th' not in app_css:
    app_css += table_th_replacement

with open(app_css_path, 'w', encoding='utf-8') as f:
    f.write(app_css)

print("Vibrant Medical Hospital Blue theme tokens applied.")

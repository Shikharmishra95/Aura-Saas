import re

filepath_index = r'c:\Users\shiva\Desktop\AAA\frontend\src\index.css'
filepath_app_css = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.css'

# Update index.css design tokens
with open(filepath_index, 'r', encoding='utf-8') as f:
    content_index = f.read()

old_tokens = '''  --bg-main: #F8FAFC;
  --bg-surface: #FFFFFF;
  --bg-card: #FFFFFF;
  --bg-card-hover: #F1F5F9;
  --bg-muted: #F1F5F9;
  
  /* Royal Blue Primary Accents */
  --primary: #2563EB;
  --primary-hover: #1D4ED8;
  --primary-soft: #EFF6FF;
  --primary-border: #BFDBFE;'''

new_tokens = '''  --bg-main: #F0F4FA;
  --bg-surface: #FFFFFF;
  --bg-card: #FFFFFF;
  --bg-card-hover: #EFF6FF;
  --bg-muted: #E2E8F0;
  
  /* Medical Hospital Blue Primary Accents */
  --primary: #2563EB;
  --primary-hover: #1D4ED8;
  --primary-soft: #EFF6FF;
  --primary-border: #BFDBFE;
  --medical-navy: #1E3A8A;
  --medical-header-bg: #F0F7FF;'''

if old_tokens in content_index:
    content_index = content_index.replace(old_tokens, new_tokens)

with open(filepath_index, 'w', encoding='utf-8') as f:
    f.write(content_index)

# Update App.css with Medical Blue theme enhancements
with open(filepath_app_css, 'r', encoding='utf-8') as f:
    content_app_css = f.read()

medical_blue_css_rules = '''

/* ==========================================================================
   🏥 VIBRANT MEDICAL HOSPITAL BLUE THEME ENHANCEMENTS
   ========================================================================== */

body, #root, .dashboard-layout {
  background-color: #F0F4FA !important;
}

/* Header with Soft Blue Accent Border */
.dashboard-header {
  background-color: #FFFFFF !important;
  border-bottom: 2px solid #DBEAFE !important;
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.06) !important;
}

/* Left Sidebar with Clean Medical Blue Border & Active Fill */
aside {
  background-color: #FFFFFF !important;
  border-right: 1.5px solid #DBEAFE !important;
}

.sidebar-btn {
  border-radius: 10px !important;
  font-weight: 600 !important;
  color: #334155 !important;
  transition: all 0.2s ease !important;
}

.sidebar-btn:hover {
  background-color: #EFF6FF !important;
  color: #2563EB !important;
}

.sidebar-btn.active {
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
  color: #FFFFFF !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
}

/* Tables with Soft Medical Blue Header */
.custom-table th {
  background-color: #EFF6FF !important;
  color: #1E40AF !important;
  font-weight: 700 !important;
  border-bottom: 1.5px solid #BFDBFE !important;
}

.custom-table td {
  border-bottom: 1px solid #E2E8F0 !important;
  color: #0F172A !important;
}

.custom-table tr:hover {
  background-color: #F8FAFC !important;
}

/* Medical Blue Cards & Panels */
.glass-panel, .card, .p-card {
  background-color: #FFFFFF !important;
  border: 1.5px solid #E2E8F0 !important;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05) !important;
}

/* Tabs Accent Line */
.tab-btn.active {
  border-bottom: 3px solid #2563EB !important;
  color: #2563EB !important;
  font-weight: 700 !important;
}
'''

if "VIBRANT MEDICAL HOSPITAL BLUE THEME ENHANCEMENTS" not in content_app_css:
    content_app_css += "\n" + medical_blue_css_rules

with open(filepath_app_css, 'w', encoding='utf-8') as f:
    f.write(content_app_css)

print("Hospital Blue theme rules injected into index.css and App.css successfully.")

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.css'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_rule = '''.glass-panel, .card, .p-card {
  background-color: #FFFFFF !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow-sm) !important;
  border-radius: var(--radius) !important;
}'''

new_rule = '''.glass-panel, .card, .p-card {
  background-color: #FFFFFF !important;
  color: #0F172A !important;
  border: 1.5px solid var(--border) !important;
  box-shadow: var(--shadow-sm) !important;
  border-radius: var(--radius) !important;
}'''

if old_rule in content:
    content = content.replace(old_rule, new_rule)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.css glass-panel card text color rule updated.")

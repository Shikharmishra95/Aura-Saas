filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.css'

with open(filepath, 'a', encoding='utf-8') as f:
    f.write('''

/* Booking Time Slots 4-Column Responsive Grid Layout */
.slots-grid {
  display: grid !important;
  grid-template-columns: repeat(4, 1fr) !important;
  gap: 8px !important;
  margin-top: 10px;
}

@media (max-width: 768px) {
  .slots-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
''')

print("App.css updated with 4-column slots-grid rule.")

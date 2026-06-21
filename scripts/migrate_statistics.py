\"""
Скрипт для миграции с DB().increment_book_download_count на stats.increment_download_count
\"""
import re

# Читаем файл
with open('src/ui/pages/pdf_reader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем вызовы
content = re.sub(
    r"Database\(\)\.increment_book_download_count\(self\.book\.id\)",
    "stats.increment_download_count(self.book.id)",
    content
)

# Сохраняем обратно
with open('src/ui/pages/pdf_reader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Замена выполнена!")
\"
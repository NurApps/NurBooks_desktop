import sqlite3
import json

conn = sqlite3.connect('data/books.db')
c = conn.cursor()
c.execute('SELECT * FROM books ORDER BY id')
rows = c.fetchall()
cols = [d[0] for d in c.description]
books = [dict(zip(cols, r)) for r in rows]

with open('books_export.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=2)

print(f'Exported {len(books)} books to books_export.json')
conn.close()

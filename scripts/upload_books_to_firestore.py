"""
Скрипт для загрузки всех книг из SQLite в Firestore.

Читает данные напрямую из data/books.db и создаёт документы в коллекции books.
Обновляет поля cover и pdf на формат raw GitHub URL.
"""

import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))


def convert_github_url(url):
    """Конвертирует GitHub blob URL в raw URL для прямого скачивания"""
    if not url or not url.startswith('https://github.com/'):
        return url

    # Формат: https://github.com/owner/repo/blob/main/path/to/file
    # Конвертируем в: https://raw.githubusercontent.com/owner/repo/main/path/to/file
    match = re.match(
        r'https://github\.com/([^/]+)/([^/]+)/blob/(.+)/(.+)',
        url
    )
    if match:
        owner = match.group(1)
        repo = match.group(2)
        branch = match.group(3)
        filepath = match.group(4)
        return f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}'

    # Уже releases/download - оставляем как есть
    if 'releases/download' in url:
        return url

    return url


def migrate_to_firestore():
    """Загружает все книги из SQLite в Firestore"""

    print("=" * 60)
    print("SQLite -> Firestore Migration")
    print("=" * 60)
    print()

    # Проверяем serviceAccountKey.json
    service_account_path = "serviceAccountKey.json"
    if not os.path.exists(service_account_path):
        from src.config import BASE_PATH
        service_account_path = os.path.join(BASE_PATH, "serviceAccountKey.json")

    if not os.path.exists(service_account_path):
        print("[ERR] serviceAccountKey.json не найден!")
        return

    print("[OK] serviceAccountKey.json найден")

    # Читаем SQLite
    import sqlite3
    conn = sqlite3.connect('data/books.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM books ORDER BY id')
    rows = c.fetchall()
    total = len(rows)
    print(f"[OK] Найдено {total} книг в SQLite")
    print()

    # Инициализируем Firebase
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if firebase_admin._DEFAULT_APP_NAME not in firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'projectId': 'nurbooks-a0eae'
            })

        db = firestore.client()
        print("[OK] Подключено к Firestore")
        print()
    except Exception as e:
        print(f"[ERR] Ошибка подключения к Firestore: {e}")
        return

    # Мигрируем книги
    success = 0
    failed = 0

    for i, row in enumerate(rows, 1):
        book_id = row['id']
        title = row['title'][:30]  # Для отображения

        # Конвертируем URL
        cover_url = convert_github_url(row['cover'])
        pdf_url = convert_github_url(row['pdf'])

        doc_data = {
            'id': book_id,
            'title': row['title'],
            'author': row['author'],
            'category': row['category'],
            'year': row['year'],
            'description': row['description'],
            'cover': cover_url,
            'pdf': pdf_url,
            'fileSize': row['file_size'],
            'pages': row['pages'],
            'copyrightProtected': bool(row['copyright_protected']),
            'viewCount': row['view_count'],
            'downloadCount': row['download_count'],
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        try:
            doc_ref = db.collection('books').document(str(book_id))
            doc_ref.set(doc_data)
            print(f"  [{i}/{total}] OK: {title}... (ID: {book_id})")
            print(f"       Cover: {cover_url[:60]}...")
            print(f"       PDF:   {pdf_url[:60]}...")
            success += 1
        except Exception as e:
            print(f"  [{i}/{total}] ERR: {title}... ({e})")
            failed += 1

    print()
    print("=" * 60)
    print(f"Результат: {success} успешно, {failed} ошибок из {total}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    migrate_to_firestore()

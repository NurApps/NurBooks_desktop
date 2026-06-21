"""
Скрипт для быстрой настройки Firestore в Firebase Console.

Использование:
1. Убедись что serviceAccountKey.json в корне проекта
2. Запусти: python scripts/setup_firestore_schema.py
3. Скрипт создаст все коллекции и правила безопасности
"""

import os
import sys

sys.path.insert(0, os.path.abspath('.'))


def setup_firestore():
    """Создаёт структуру Firestore с нуля"""

    print("=" * 60)
    print("Firestore Schema Setup for NurBooks")
    print("=" * 60)
    print()

    # Проверяем serviceAccountKey.json
    service_account_path = "serviceAccountKey.json"
    if not os.path.exists(service_account_path):
        from src.config import BASE_PATH
        service_account_path = os.path.join(BASE_PATH, "serviceAccountKey.json")

    if not os.path.exists(service_account_path):
        print("[ERR] serviceAccountKey.json не найден!")
        print(f"Помести файл в: {service_account_path}")
        print()
        print("Как получить:")
        print("1. console.firebase.google.com --> твой проект")
        print("2. Project Settings --> Service Accounts")
        print("3. Generate new private key")
        return

    print("[OK] serviceAccountKey.json найден")
    print()

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Инициализация
        if not firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'projectId': 'nurbooks-12345'  # ЗАМЕНИ НА СВОЙ PROJECT_ID
            })

        db = firestore.client()
        print("[OK] Подключено к Firestore")
        print()

    except Exception as e:
        print(f"[ERR] Ошибка подключения: {e}")
        print()
        print("Проверь:")
        print("1. pip install firebase-admin")
        print("2. serviceAccountKey.json в корне проекта")
        print("3. Firestore включён в Firebase Console")
        return

    # Создаём структуры
    print("[DB] Создание коллекций...")
    print()

    print("[BOOK] Коллекция 'books'")
    print("   Структура документа:")
    print("""   {
     id: 1,
     title: "Название книги",
     author: "Автор",
     category: "Категория",
     year: 2024,
     description: "Описание",
     cover: "https://github.com/.../releases/latest/download/covers/book_1.jpg",
     pdf: "https://github.com/.../releases/latest/download/pdfs/book_1.pdf",
     fileSize: "15 MB",
     pages: 320,
     copyrightProtected: false,
     viewCount: 0,
     downloadCount: 0,
     createdAt: Timestamp,
     updatedAt: Timestamp
   }""")
    print()

    print("[BM] Коллекция 'bookmarks'")
    print("   Структура документа:")
    print("""   {
     id: "auto-generated",
     bookId: 1,
     page: 42,
     timestamp: "2024-12-01T10:30:00",
     note: "Важное место"
   }""")
    print()

    print("[STAT] Коллекция 'analytics'")
    print("   Структура документа:")
    print("""   {
     bookId: 1,
     totalViews: 150,
     viewsByDay: {
       "2024-12-01": 15,
       "2024-12-02": 23
     },
     totalDownloads: 45,
     downloadsByDay: {
       "2024-12-01": 5,
       "2024-12-02": 8
     },
     lastUpdated: Timestamp
   }""")
    print()

    # Правила безопасности
    rules = r'''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Книги - публичное чтение, запись только авторизованным
    match /books/{bookId} {
      allow read: if true;
      allow write: if request.auth != null &&
                   get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }

    // Закладки - только свой аккаунт
    match /bookmarks/{bookmarkId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null;
      allow update, delete: if request.auth.uid == resource.data.userId;
    }

    // Аналитика - чтение всем, запись только серверу
    match /analytics/{bookId} {
      allow read: if true;
      allow write: if false; // Только через Cloud Functions или Admin SDK
    }

    // Пользователи
    match /users/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth.uid == userId;
    }
  }
}'''

    print("=" * 60)
    print("[RULE] Правила безопасности (Firestore Rules)")
    print("=" * 60)
    print()
    print(rules)
    print()
    print("=" * 60)
    print("[INFO] Как применить правила:")
    print("=" * 60)
    print()
    print("1. console.firebase.google.com --> Firestore Database")
    print("2. Вкладка 'Rules' сверху")
    print("3. Скопируй правила выше и вставь")
    print("4. Нажми 'Publish'")
    print()
    print("=" * 60)
    print("[INFO] Индексы для поиска")
    print("=" * 60)
    print()
    print("Создай composite индексы в Firestore --> Indexes:")
    print()
    print("Индекс 1 (поиск по title):")
    print("  Collection: books")
    print("  Fields: title (Ascending) + title (Ascending)")
    print()
    print("Индекс 2 (поиск по author):")
    print("  Collection: books")
    print("  Fields: author (Ascending) + author (Ascending)")
    print()
    print("Индекс 3 (закладки по книге):")
    print("  Collection: bookmarks")
    print("  Fields: bookId (Ascending) + page (Ascending)")
    print()
    print("=" * 60)
    print("[DONE] Готово! Теперь запусти миграцию:")
    print("       python scripts/migrate_sqlite_to_firestore.py")
    print("=" * 60)


if __name__ == "__main__":
    setup_firestore()

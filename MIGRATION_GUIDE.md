# 🚀 Миграция на Firebase: Quick Start Guide

## 📌 Текущее состояние проекта

### ✅ Уже стабилизировано:
1. **Централизованная статистика** (`StatisticsManager`)
   - Все вызовы `view_count`/`download_count` идут через `stats`
   - При миграции на Firebase просто заменится реализация `StatisticsManager`
2. **FirebaseClient skeleton** (`src/core/firebase_client.py`)
   - Заглушка для всех Firebase методов
   - Готова к интеграции при наличии serviceAccountKey.json

---

## 🔧 Шаг 1: Настройка Firebase проекта

### 1.1 Создать проект в [console.firebase.google.com]
- Имя: `NurBooks`
- Страна: Россия
- Google Analytics: **НЕ подключать** (мы будем использовать Firestore напрямую)

### 1.2 Включить необходимые сервисы

| Сервис | Статус | Описание |
|--------|--------|----------|
| **Firestore Database** | ⚠️ Test Mode | База данных для книг, статистики |
| **Firebase Storage** | ⚠️ Test Mode | Хранение PDF и обложек |
| **Authentication** | ❌ Пока не нужен | На следующем этапе |

### 1.3 Настроить Firestore rules (opens in test mode initially)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Книги - публичные для чтения
    match /books/{bookId} {
      allow read: if true;
      allow write: if false; // Защита от случайной модификации
    }
    
    // Аналитика - неограниченное чтение
    match /analytics/{bookId} {
      allow read: if true;
      allow write: if false;
    }
    
    // Пользовательские данные (пока не используется)
    match /users/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### 1.4 Настроить Storage rules (test mode)

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Обложки (публичные)
    match /covers/{bookId} {
      allow read: if true;
      allow write: if false;
    }
    
    // PDF (только авторизованные — пока запретим)
    match /pdfs/{bookId} {
      allow read: if false; // Пока запретим, добавим на следующем этапе
      allow write: if false;
    }
  }
}
```

---

## 📥 Шаг 2: Получение serviceAccountKey.json

### 2.1 Создать service account
1. В консоли Firebase: **Project Settings** → **Service Accounts**
2. Нажать **Generate new private key**
3. Сохранить `serviceAccountKey.json` в папку проекта (но НЕ committing в git!)

### 2.2 Добавить `.gitignore` для ключа
```gitignore
# Firebase
serviceAccountKey.json
firebase-debug.log
```

---

## 🔌 Шаг 3: Интеграция в код

### 3.1 Установить Firebase Admin SDK
```bash
pip install firebase-admin
```

### 3.2 Обновить `src/config.py`
Раскомментировать реальные значения:

```python
# src/config.py

class FirebaseConfig:
    # 🔥 ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ
    PROJECT_ID = "nurbooks-123456"
    API_KEY = "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    AUTH_DOMAIN = "nurbooks-123456.firebaseapp.com"
    STORAGE_BUCKET = "nurbooks-123456.appspot.com"
    MESSAGING_SENDER_ID = "123456789012"
    APP_ID = "1:123456789012:web:abcdef1234567890"
    
    # 🔥 NEW: Путь к service account key (локально!)
    SERVICE_ACCOUNT_KEY_PATH = "serviceAccountKey.json"
    
    @classmethod
    def is_configured(cls):
        """Проверяет, настроен ли Firebase"""
        import os
        return (
            cls.API_KEY != "AIzaSyXXXXXXXXXXXX" and
            os.path.exists(cls.SERVICE_ACCOUNT_KEY_PATH)
        )
```

### 3.3 Обновить `src/core/firebase_client.py`
Раскомментировать реальную инициализацию:

```python
# src/core/firebase_client.py

class FirebaseClient:
    def _initialize_firebase(self, config: Dict[str, Any]):
        """
        Инициализирует Firebase
        """
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore, storage
            
            # 🔥 РАСКОММЕНТИРОВАТЬ ПОСЛЕ СОЗДАНИЯ serviceAccountKey.json
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {
                'projectId': config['projectId'],
                'storageBucket': config['storageBucket']
            })
            
            self._db = firestore.client()
            self._storage = storage.bucket()
            
            logger.info("Firebase инициализирован успешно!")
            self._initialized = True
        except Exception as e:
            logger.error(f"Ошибка инициализации Firebase: {e}", exc_info=True)
            logger.error("❌ Firebase не настроен. Используется режим Offline.")
```

### 3.4 Заменить `StatisticsManager` на Firebase реализацию

```python
# src/core/statistics_manager.py

class StatisticsManager:
    # ... existing code ...
    
    def increment_view_count(self, book_id: int) -> bool:
        """
        Увеличивает счётчик просмотров (Firebase version)
        """
        try:
            from src.core.firebase_client import firebase_client
            
            if firebase_client.is_initialized():
                # Используем Firebase
                return firebase_client.increment_view_count(book_id)
            else:
                # Fallback на SQLite
                return self._legacy_increment_view_count(book_id)
        except Exception as e:
            logger.error(f"Ошибка при увеличении просмотров: {e}", exc_info=True)
            return False
    
    def _legacy_increment_view_count(self, book_id: int) -> bool:
        """
        Старая SQLite реализация (fallback)
        """
        try:
            success = self.database.increment_book_view_count(book_id)
            if success:
                logger.debug(f"Счётчик просмотров увеличен для книги ID={book_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при увеличении просмотров (SQLite fallback): {e}", exc_info=True)
            return False
```

---

## 📦 Шаг 4: Миграция данных из SQLite → Firestore

### 4.1 Создать скрипт миграции
```python
# scripts/migrate_to_firestore.py

import firebase_admin
from firebase_admin import credentials, firestore
import sqlite3
import json
import os
from pathlib import Path

def migrate_to_firestore():
    """
    Мигрирует данные из SQLite → Firestore
    """
    # Подключение к Firebase
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'projectId': "nurbooks-123456",
        'storageBucket': "nurbooks-123456.appspot.com"
    })
    
    db = firestore.client()
    
    # Подключение к SQLite
    conn = sqlite3.connect("data/books.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    
    # Миграция книг
    for book in books:
        book_data = {
            'id': book[0],
            'title': book[1],
            'author': book[2],
            'category': book[3],
            'year': book[4],
            'description': book[5],
            'coverUrl': f"https://storage.googleapis.com/nurbooks-123456.appspot.com/covers/{book[0]}.jpg",
            'pdfUrl': f"https://storage.googleapis.com/nurbooks-123456.appspot.com/pdfs/{book[0]}.pdf",
            'fileSize': book[7],
            'pages': book[8],
            'copyrightProtected': bool(book[9]),
            'viewCount': book[10],
            'downloadCount': book[11],
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('books').document(str(book[0])).set(book_data)
    
    conn.close()
    print(f"✅ Migrated {len(books)} books to Firestore!")

if __name__ == "__main__":
    migrate_to_firestore()
```

### 4.2 Запустить миграцию
```bash
# Сначала загрузите обложки и PDF в Firebase Storage
# ( manifold way через gsutil или Firebase Console)

# Запустить миграцию
python scripts/migrate_to_firestore.py
```

---

## ⚠️ Критичные замечания

### 1. **Безопасность PDF файлов**
- Сейчас в `FirebaseStorage.rules` запрещено чтение PDF (`allow read: if false`)
- После включения авторизации нужно будет разрешить чтение только для авторизованных пользователей

### 2. **Обновление UI при миграции**
- Прокси в `StatisticsManager` уже готов — при падении Firebase он автоматически вернётся к SQLite
- No code changes needed в UI!

### 3. **Rate Limits**
- Free tier Firestore: **50k reads / 20k writes / day**
- Если превысим — перейдём на Blaze plan ($0.06 per 100k reads)

---

## 🎯 What to do next?

1. ✅ [DONE] Stabilize local analytics (StatisticsManager)
2. 🔜 Create Firebase project и получить serviceAccountKey.json
3. 🔜 Настроить Firebase Storage (upload covers + PDFs)
4. 🔜 Запустить миграцию SQLite → Firestore
5. 🔜 Включить Firebase Analytics (отслеживание UA)
6. 🔜 Добавить авторизацию (Email/Password + Guest login)

---

## 📞 Вопросы и поддержка

Если возникли проблемы:
- ✅ Сначала проверить `serviceAccountKey.json` (права на чтение/запись)
- ✅ Проверить Firestore rules (test mode)
- ✅ Убедиться, что Firebase SDK установлен (`pip install firebase-admin`)

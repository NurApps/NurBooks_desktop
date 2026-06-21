# План миграции на Firebase для NurBooks

## 1. Обзор Firebase Services

```
Firebase Services for NurBooks:
├── Firestore Database ( NosQL для книг, пользователей, закладок)
├── Firebase Authentication ( JWT через email/password, guest login)
├── Firebase Storage ( хранение PDF файлов и oblojek)
├── Firebase Analytics ( отслеживание просмотров и скачиваний)
├── Firebase Cloud Messaging ( push-уведомления)
├── Firebase Remote Config ( динамические настройки)
└── Cloud Functions ( обработка событий, cache invalidation)
```

## 2. Структура Firestore Database

### 2.1 Коллекция `books`

```json
 books : {
  bookId: {
    id: number,
    title: string,
    author: string,
    category: string,
    year: number,
    description: string,
    coverUrl: string (Firebase Storage URL),
    pdfUrl: string (Firebase Storage URL),
    fileSize: string,
    pages: number,
    copyrightProtected: boolean,
    viewCount: number,
    downloadCount: number,
    createdAt: timestamp,
    updatedAt: timestamp
  }
}
```

### 2.2 Коллекция `users`

```json
users: {
  userId: {
    username: string,
    email: string,
    displayName: string,
    avatarUrl: string,
    createdAt: timestamp,
    lastActive: timestamp,
    preferences: {
      theme: "light" | "dark",
      language: "ru",
      pdfReader: "ask" | "builtin" | "system",
      cloudStorageEnabled: boolean
    },
    statistics: {
      totalViews: number,
      totalDownloads: number,
      librarySize: number
    }
  }
}
```

### 2.3 Коллекция `libraries` (Personal Library)

```json
libraries: {
  userId: {
    books: ["bookId1", "bookId2", ...] // Список ID книг пользователя
  }
}
```

### 2.4 Коллекция `favorites`

```json
favorites: {
  userId: {
    books: ["bookId1", "bookId2", ...]
  }
}
```

### 2.5 Коллекция `bookmarks`

```json
bookmarks: {
  userId_bookId: {
    bookId: string,
    userId: string,
    page: number,
    timestamp: timestamp,
    note: string
  }
}
```

### 2.6 Коллекция `analytics` (Aggregated Stats)

```json
analytics: {
  bookId: {
    bookId: string,
    totalViews: number,
    viewsByDay: {
      "2024-12-01": 15,
      "2024-12-02": 23,
      ...
    },
    totalDownloads: number,
    downloadsByDay: {
      "2024-12-01": 5,
      ...
    },
    lastUpdated: timestamp
  }
}
```

## 3. Firebase Authentication

### 3.1 Поддерживаемые методы входа

```
1. Email/Password (основной метод)
2. Guest Login (гостевой режим без регистрации)
3. Google Sign-In (опционально)
4.Anonymous auth for bookmarks/sync (анонимные сессии)
```

### 3.2 Структура JWT Claims

```python
{
  "sub": "userId",          # Идентификатор пользователя
  "email": "user@example.com",
  "name": "User Name",
  "role": "user",           # user | admin
  "iat": 1702900000,        # issued at
  "exp": 1703504800         # expires in 7 days
}
```

### 3.3 Security Rules для Firestore

```javascript
// Firestore Rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Книги - публичные для чтения
    match /books/{bookId} {
      allow read: if true;
      allow write: if request.auth != null && 
                   get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Пользовательские данные
    match /users/{userId} {
      allow read: if request.auth.uid == userId || request.auth != null;
      allow write: if request.auth.uid == userId;
    }
    
    // Библиотека
    match /libraries/{userId} {
      allow read: if request.auth.uid == userId;
      allow write: if request.auth.uid == userId;
    }
    
    // Закладки
    match /bookmarks/{bookmarkId} {
      allow read, write: if request.auth != null && 
                         get(/databases/$(database)/documents/users/$(request.auth.uid)).data != null;
    }
    
    // Аналитика - чтение всем, запись сервером
    match /analytics/{bookId} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

## 4. Firebase Storage Structure

```
nurbooks-storage/
├── covers/                  # Обложки книг
│   ├── book_123.jpg
│   ├── book_456.jpg
│   └── ...
├── pdfs/                    # PDF файлы
│   ├── book_123.pdf
│   ├── book_456.pdf
│   └── ...
└── thumbnails/              # Миниатюры
    ├── book_123_tn.jpg
    └── ...
```

### 4.1 Security Rules for Storage

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    
    // Обложки - публичное чтение
    match /covers/{bookId} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    
    // PDF файлы - только авторизованные
    match /pdfs/{bookId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
    
    // Миниатюры - публичное чтение
    match /thumbnails/{bookId} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

## 5. Integration Plan

### Phase 1: Database Migration (Week 1)

```
1. Создать Firebase project
2. Настроить Firestore в test mode
3. Мигрировать книги из books.db → Firestore
4. Мигрировать авторов и категории
5. Создать индексы для оптимизации запросов
```

Migration script:
```python
# scripts/migrate_to_firestore.py

import firebase_admin
from firebase_admin import credentials, firestore
import json
import sqlite3

def migrate_books_to_firestore():
    # Подключение к SQLite
    conn = sqlite3.connect('data/books.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    
    # Подключение к Firestore
    db = firestore.client()
    
    # Миграция
    for book in books:
        book_data = {
            'id': book[0],
            'title': book[1],
            'author': book[2],
            'category': book[3],
            'year': book[4],
            'description': book[5],
            'coverUrl': convert_cover_url_to_firebase(book[6]),
            'pdfUrl': convert_pdf_url_to_firebase(book[7]),
            'fileSize': book[8],
            'pages': book[9],
            'copyrightProtected': bool(book[10]),
            'viewCount': book[11],
            'downloadCount': book[12],
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }
        db.collection('books').document(str(book[0])).set(book_data)
    
    conn.close()
    print(f"Migrated {len(books)} books to Firestore")
```

### Phase 2: Authentication Setup (Week 2)

```
1. Настроить Email/Password authentication
2. Создать систему guest login
3. Имплементировать JWT токены
4. Настроить security rules
5. Тестирование авторизации
```

### Phase 3: Storage Migration (Week 3)

```
1. Создать Firebase Storage bucket
2. Скачать все обложки из SQLite/ lokal
3. Загрузить в Firebase Storage
4. Обновить URL в Firestore
5. Проверить CDN кэширование
```

### Phase 4: Real-time Sync (Week 4)

```
1. Реализовать listen на libraries
2. Реализовать sync favorites
3. Real-time bookmarks
4. Offline capabilities (Firebase Local Persistence)
```

## 6.更新 wellbeing_ api

### 6.1 описание API endpoints

```python
# src/api/firebase_client.py

import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
from typing import Optional, List, Dict, Any
from src.core.models import Book

class FirebaseClient:
    def __init__(self):
        cred = credentials.Certificate("path/to/serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'nurbooks.appspot.com'
        })
        self.db = firestore.client()
        self.storage = storage.bucket()
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload file to Firebase Storage"""
        blob = self.storage.blob(remote_path)
        blob.upload_from_filename(local_path)
        blob.make_public()
        return blob.public_url
    
    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Get book by ID from Firestore"""
        doc = self.db.collection('books').document(str(book_id)).get()
        if doc.exists:
            data = doc.to_dict()
            return Book(**data)
        return None
    
    def search_books(self, query: str) -> List[Book]:
        """Search books by title or author"""
        books = []
        
        # Using Firestore composite indexes
        title_query = self.db.collection('books').where('title', '>=', query).where('title', '<=', query + 'z')
        author_query = self.db.collection('books').where('author', '>=', query).where('author', '<=', query + 'z')
        
        for doc in title_query.stream():
            books.append(Book(**doc.to_dict()))
        for doc in author_query.stream():
            if doc.to_dict()['id'] not in [b.id for b in books]:
                books.append(Book(**doc.to_dict()))
        
        return books
    
    def increment_view_count(self, book_id: int) -> bool:
        """Increment view count atomically"""
        book_ref = self.db.collection('books').document(str(book_id))
        self.db.run_transaction(lambda txn: txn.update(book_ref, 'viewCount', firestore.Increment(1)))
        return True
    
    def add_to_library(self, user_id: str, book_id: int) -> bool:
        """Add book to user's library"""
        library_ref = self.db.collection('libraries').document(user_id)
        self.db.update(library_ref, {
            'books': firestore.ArrayUnion([str(book_id)])
        })
        return True
    
    def get_user_library(self, user_id: str) -> List[str]:
        """Get user's library book IDs"""
        doc = self.db.collection('libraries').document(user_id).get()
        if doc.exists:
            return doc.to_dict().get('books', [])
        return []
```

### 6.2 Security Validation

```python
# Middleware для проверки JWT
from src.api.firebase_client import FirebaseClient
from fastapi import Header, HTTPException
import jwt

def verify_firebase_token(x_auth_token: str = Header(None)):
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Missing token")
    
    try:
        decoded_token = firebase_admin.auth.verify_id_token(x_auth_token)
        return decoded_token['uid']
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

## 7. Файлы, которые нужно создать

```
src/
├── core/
│   ├── firebase_client.py      # Новый: Firebase клиент для работы с API
│   ├── firebase_auth.py        # Новый: Управление аутентификацией
│   └── analytics.py           # Обновленный: Добавить Firebase Analytics
├── api/
│   ├── server.py              # Новый: FastAPI сервер
│   └── firebase_client.py     # Новый: Client для API
└── utils/
    └── migration.py           # Новый: Скрипты миграции
```

## 8. Тестирование и Продакшн

### 8.1 Тестирование

```bash
# Local Testing
firebase emulators:start --only firestore,storage,auth

# Run tests
python tests/test_firebase_migration.py
python tests/test_auth.py
```

### 8.2 Deployment

```bash
# Deploy to Firebase
firebase deploy --only firestore:rules,storage,functions

# Environment variables
export FIREBASE_PROJECT_ID=nurbooks-12345
export SERVICE_ACCOUNT_KEY=path/to/key.json
```

## 9. Cost estimates

```
Firebase Free Tier:
├── Firestore: 50k reads, 20k writes per day
├── Storage: 5GB storage, 1GB download per day
└── Auth: Unlimited users

Estimated costs for 10k users:
├── Firestore: $0 (within free tier)
├── Storage: $0 (within free tier)
└── Total: $0/month
```

## 10. Roadmap

```
Q1 2025: Firebase Migration
├── Week 1: Firestore setup + migration
├── Week 2: Authentication
├── Week 3: Storage migration
├── Week 4: Real-time sync
└── Week 5: Testing + deployment

Q2 2025: Features
├── push-уведомления (Cloud Messaging)
├── offline-first (Local Persistence)
└── analytics dashboard
```

---

**Next Steps:**
1. Создать Firebase project в console.firebase.google.com
2. Настроить Email authentication
3. Создать service account key
4. Запустить миграцию книг
"""
Скрипт миграции данных из SQLite в Firestore

Использование:
    python migrate_sqlite_to_firestore.py

При первом запуске:
    1. Убедитесь, что serviceAccountKey.json в корне проекта
    2. Убедитесь, чтоFirebase настроен в src/config.py
    3. Запустите скрипт
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
import sys

# Добавляем путь к src
sys.path.insert(0, os.path.abspath('.'))

from src.core.database import Database
from src.core.models import Book
from src.core.logger import get_logger
from scripts.firestore_db_manager import FirestoreBookManager

logger = get_logger(__name__)

class SQLiteToFirestoreMigrator:
    """
    Мигратор данных из SQLite в Firestore.
    
    Копирует:
    - Все книги из books.db
    - Все закладки из bookmarks
    """
    
    def __init__(self):
        self.sqlite_db = Database()
        self.firestore_db = FirestoreBookManager()
    
    def migrate_books(self) -> dict:
        """
        Мигрирует все книги из SQLite в Firestore.
        
        Returns:
            dict с результатами миграции
        """
        logger.info("Начало миграции книг из SQLite в Firestore")
        
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Получаем все книги из SQLite
        books = self.sqlite_db.get_all_books()
        result['total'] = len(books)
        
        logger.info(f"Найдено {len(books)} книг в SQLite")
        
        for book in books:
            try:
                # Проверяем, существует ли уже в Firestore
                exists = self.firestore_db.get_book_by_id(book.id)
                if exists:
                    logger.warning(f"Книга {book.id} уже существует в Firestore, пропускаем")
                    result['skipped'] += 1
                    continue
                
                # Добавляем книгу в Firestore
                status = self.firestore_db.add_book(book)
                
                if status == "success":
                    result['success'] += 1
                    logger.info(f"Книга '{book.title}' (ID: {book.id}) успешно мигрирована")
                elif status == "id_exists":
                    logger.warning(f"Книга {book.id} уже существует в Firestore, пропускаем")
                    result['skipped'] += 1
                else:
                    raise Exception(f"Ошибка добавления книги: {status}")
                    
            except Exception as e:
                result['failed'] += 1
                result['errors'].append({
                    'book_id': book.id,
                    'title': book.title,
                    'error': str(e)
                })
                logger.error(f"Ошибка миграции книги {book.id} ({book.title}): {e}")
        
        logger.info(f"Миграция завершена: {result}")
        return result
    
    def migrate_bookmarks(self) -> dict:
        """
        Мигрирует все закладки из SQLite в Firestore.
        
        Returns:
            dict с результатами миграции
        """
        logger.info("Начало миграции закладок из SQLite в Firestore")
        
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Получаем все закладки из SQLite
        all_bookmarks = self.sqlite_db.get_all_bookmarks_with_books()
        result['total'] = len(all_bookmarks)
        
        logger.info(f"Найдено {len(all_bookmarks)} закладок в SQLite")
        
        for bookmark, book in all_bookmarks:
            try:
                # Проверяем, существует ли уже в Firestore
                existing = self.firestore_db.get_bookmarks_by_book(book.id)
                if any(b.page_number == bookmark.page_number for b in existing):
                    logger.warning(f"Закладка для книги {book.id}, страница {bookmark.page_number} уже существует")
                    result['skipped'] += 1
                    continue
                
                # Добавляем закладку в Firestore
                status = self.firestore_db.add_bookmark(bookmark)
                
                if status:
                    result['success'] += 1
                    logger.info(f"Закладка для книги {book.id}, страница {bookmark.page_number} успешно мигрирована")
                else:
                    raise Exception("Не удалось добавить закладку")
                    
            except Exception as e:
                result['failed'] += 1
                result['errors'].append({
                    'book_id': bookmark.book_id,
                    'page': bookmark.page_number,
                    'error': str(e)
                })
                logger.error(f"Ошибка миграции закладки для книги {bookmark.book_id}, страница {bookmark.page_number}: {e}")
        
        logger.info(f"Миграция закладок завершена: {result}")
        return result
    
    def full_migration(self) -> dict:
        """
        Полная миграция: книги и закладки.
        
        Returns:
            dict с полным результатом
        """
        books_result = self.migrate_books()
        bookmarks_result = self.migrate_bookmarks()
        
        return {
            'books': books_result,
            'bookmarks': bookmarks_result,
            'total_books_migrated': books_result['success'],
            'total_bookmarks_migrated': bookmarks_result['success']
        }


def main():
    """
    Основная функция миграции.
    """
    print("="*60)
    print("SQLite → Firestore Миграция")
    print("="*60)
    print()
    
    # Проверяем serviceAccountKey.json
    service_account_path = "serviceAccountKey.json"
    if not os.path.exists(service_account_path):
        base_path = os.path.abspath('.')
        service_account_path = os.path.join(base_path, "serviceAccountKey.json")
    
    if not os.path.exists(service_account_path):
        print(f"❌ ОШИБКА: serviceAccountKey.json не найден!")
        print(f"Пожалуйста, создайте service account в Firebase Console и загрузите ключ в:")
        print(f"{service_account_path}")
        print()
        return
    
    print(f"✅ serviceAccountKey.json найден")
    print()
    
    # Создаем мигратор
    migrator = SQLiteToFirestoreMigrator()
    
    # Проверяем подключение к Firestore
    if not migrator.firestore_db.is_initialized():
        print("❌ ОШИБКА: Не удалось подключиться к Firestore!")
        print("Проверьте консоль для подробной информации.")
        return
    
    print("✅ Подключение к Firestore успешно")
    print()
    
    # Запрашиваем подтверждение
    print("ИНФОРМАЦИЯ:")
    print(f"- Книг в SQLite: {len(migrator.sqlite_db.get_all_books())}")
    print(f"- Закладок в SQLite: {len(migrator.sqlite_db.get_all_bookmarks_with_books())}")
    print()
    
    response = input("Начать миграцию? (y/N): ").strip().lower()
    if response != 'y':
        print("Миграция отменена")
        return
    
    print()
    print("Запуск миграции...")
    print()
    
    # Запускаем полную миграцию
    result = migrator.full_migration()
    
    # Выводим результат
    print()
    print("="*60)
    print("Results")
    print("="*60)
    print()
    
    print("📊_books:")
    print(f"   ⬆️  Total: {result['books']['total']}")
    print(f"   ✅ Success: {result['books']['success']}")
    print(f"   ⚠️  Skipped: {result['books']['skipped']}")
    print(f"   ❌ Failed: {result['books']['failed']}")
    
    if result['books']['errors']:
        print()
        print("   ❌ Errors:")
        for error in result['books']['errors'][:5]:  # Показываем первые 5
            print(f"      - Book ID {error['book_id']}: {error['error']}")
        if len(result['books']['errors']) > 5:
            print(f"      ... и еще {len(result['books']['errors']) - 5} ошибок")
    
    print()
    print("📚 Bookmarks:")
    print(f"   ⬆️  Total: {result['bookmarks']['total']}")
    print(f"   ✅ Success: {result['bookmarks']['success']}")
    print(f"   ⚠️  Skipped: {result['bookmarks']['skipped']}")
    print(f"   ❌ Failed: {result['bookmarks']['failed']}")
    
    if result['bookmarks']['errors']:
        print()
        print("   ❌ Errors:")
        for error in result['bookmarks']['errors'][:5]:
            print(f"      - Book ID {error['book_id']}, Page {error['page']}: {error['error']}")
        if len(result['bookmarks']['errors']) > 5:
            print(f"      ... и еще {len(result['bookmarks']['errors']) - 5} ошибок")
    
    print()
    print("="*60)
    print(f"✅ Миграция завершена! {result['total_books_migrated']} книг и {result['total_bookmarks_migrated']} закладок мигрировано")
    print("="*60)


if __name__ == "__main__":
    main()

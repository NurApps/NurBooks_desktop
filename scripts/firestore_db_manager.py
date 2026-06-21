"""
Менеджер базы данных Firestore для NurBooks

Предоставляет полноценный CRUD-интерфейс для работы с книгами в Firestore.
Используется как замена SQLite при работе с Firebase.
"""

from typing import Optional, List, Dict, Any
from src.core.models import Book, Bookmark
from src.core.logger import get_logger
import os

logger = get_logger(__name__)

class FirestoreBookManager:
    """
    Менедер книг в Firestore.
    
    Реализует:
    - get_book_by_id, add_book, update_book, delete_book
    - get_all_books, search_books
    - increment_view_count, increment_download_count
    - add_bookmark, get_bookmarks_by_book
    """
    
    def __init__(self):
        self._db = None
        self._initialized = False
        self._services = None
        
        self._initialize_firestore()
    
    def _initialize_firestore(self):
        """Инициализирует Firestore клиент."""
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            service_account_path = "serviceAccountKey.json"
            if not os.path.exists(service_account_path):
                from src.config import BASE_PATH
                service_account_path = os.path.join(BASE_PATH, "serviceAccountKey.json")
                if not os.path.exists(service_account_path):
                    logger.warning("Firestore не инициализирован: serviceAccountKey.json не найден")
                    self._initialized = False
                    return
            
            if not firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': "nurbooks-12345"
                })
                logger.info("Firebase App инициализирован успешно")
            
            self._db = firestore.client()
            self._initialized = True
            logger.info("FirestoreBookManager инициализирован")
            
        except firebase_admin.exceptions.AlreadyExistsError:
            logger.info("Firebase App уже инициализирован, повторное использование")
            self._db = firestore.client()
            self._initialized = True
        except Exception as e:
            logger.error(f"Ошибка инициализации Firebase: {e}", exc_info=True)
            self._initialized = False
                    return
            
            # Проверяем, не инициализировано ли уже приложение
            if not firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': "nurbooks-12345",  # TODO: FETCH FROM CONFIG
                    'storageBucket': "nurbooks-12345.appspot.com"  # TODO: FETCH FROM CONFIG
                })
                logger.info("Firebase App инициализирован успешно")
            
            self._db = firestore.client()
            self._storage = storage.bucket()
            self._initialized = True
            logger.info("FirestoreBookManager инициализирован")
            
        except firebase_admin.exceptions.AlreadyExistsError:
            logger.info("Firebase App уже инициализирован, повторное использование")
            self._db = firestore.client()
            self._storage = storage.bucket()
            self._initialized = True
        except Exception as e:
            logger.error(f"Ошибка инициализации Firebase: {e}", exc_info=True)
            self._initialized = False
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирован ли Firestore"""
        return self._initialized
    
    # ========== Books ==========
    
    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """
        Получает книгу по ID из Firestore.
        
        Args:
            book_id: ID книги
            
        Returns:
            Book объект или None
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return None
        
        try:
            doc_ref = self._db.collection('books').document(str(book_id))
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return self._doc_to_book(data)
            return None
        except Exception as e:
            logger.error(f"Ошибка получения книги {book_id}: {e}", exc_info=True)
            return None
    
    def get_all_books(self) -> List[Book]:
        """
        Получает все книги из Firestore.
        
        Returns:
            Список Book объектов
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return []
        
        try:
            books = []
            docs = self._db.collection('books').order_by('id').stream()
            
            for doc in docs:
                data = doc.to_dict()
                book = self._doc_to_book(data)
                books.append(book)
            
            logger.debug(f"Получено {len(books)} книг из Firestore")
            return books
        except Exception as e:
            logger.error(f"Ошибка получения всех книг: {e}", exc_info=True)
            return []
    
    def search_books(self, query: str) -> List[Book]:
        """
        Поиск книг по названию или автору.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список найденных книг
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return []
        
        try:
            books = []
            
            # Ищем по title
            title_query = self._db.collection('books').where('title', '>=', query).where('title', '<=', query + 'z')
            
            # Ищем по author
            author_query = self._db.collection('books').where('author', '>=', query).where('author', '<=', query + 'z')
            
            seen_ids = set()
            
            for doc in title_query.stream():
                data = doc.to_dict()
                if data['id'] not in seen_ids:
                    books.append(self._doc_to_book(data))
                    seen_ids.add(data['id'])
            
            for doc in author_query.stream():
                data = doc.to_dict()
                if data['id'] not in seen_ids:
                    books.append(self._doc_to_book(data))
                    seen_ids.add(data['id'])
            
            logger.debug(f"Найдено {len(books)} книг по запросу '{query}'")
            return books
        except Exception as e:
            logger.error(f"Ошибка поиска книг: {e}", exc_info=True)
            return []
    
    def add_book(self, book: Book) -> str:
        """
        Добавляет книгу в Firestore.
        
        Args:
            book: Book объект
            
        Returns:
            "success", "id_exists", или "error"
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return "error"
        
        try:
            # Проверяем existence
            existing = self.get_book_by_id(book.id)
            if existing:
                return "id_exists"
            
            # Добавляем PDF существование
            if self._pdf_exists(book.pdf):
                return "pdf_exists"
            
            doc_ref = self._db.collection('books').document(str(book.id))
            
            # Конвертируем_book_to_doc
            doc_data = self._book_to_doc(book)
            
            # Добавляем timestamps
            from datetime import datetime
            doc_data['createdAt'] = datetime.now()
            doc_data['updatedAt'] = datetime.now()
            
            doc_ref.set(doc_data)
            
            logger.info(f"Книга '{book.title}' добавлена в Firestore")
            return "success"
        except Exception as e:
            logger.error(f"Ошибка добавления книги: {e}", exc_info=True)
            return "error"
    
    def update_book(self, book: Book) -> bool:
        """
        Обновляет информацию о книге в Firestore.
        
        Args:
            book: Book объект с обновленными данными
            
        Returns:
            True если успешно, иначе False
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return False
        
        try:
            # Проверяем existence
            existing = self.get_book_by_id(book.id)
            if not existing:
                logger.warning(f"Книга {book.id} не найдена для редактирования")
                return False
            
            # Проверяем PDF не конфликтует
            if existing.pdf != book.pdf and self._pdf_exists(book.pdf, exclude_id=book.id):
                logger.warning(f"PDF '{book.pdf}' уже привязан к другой книге")
                return False
            
            doc_ref = self._db.collection('books').document(str(book.id))
            
            doc_data = self._book_to_doc(book)
            doc_data['updatedAt'] = __import__('datetime').datetime.now()
            
            doc_ref.update(doc_data)
            
            logger.info(f"Книга '{book.title}' обновлена в Firestore")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления книги: {e}", exc_info=True)
            return False
    
    def delete_book(self, book_id: int) -> bool:
        """
        Удаляет книгу из Firestore по ID.
        
        Args:
            book_id: ID книги
            
        Returns:
            True если успешно, иначе False
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return False
        
        try:
            # Получаем книгу для удаления файлов
            book = self.get_book_by_id(book_id)
            
            # Удаляем из Firestore
            doc_ref = self._db.collection('books').document(str(book_id))
            doc_ref.delete()
            
            logger.info(f"Книга {book_id} удалена из Firestore")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления книги {book_id}: {e}", exc_info=True)
            return False
    
    def get_book_by_pdf(self, pdf_path: str) -> Optional[Book]:
        """
        Получает книгу по пути к PDF.
        
        Args:
            pdf_path: Путь к PDF
            
        Returns:
            Book объект или None
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return None
        
        try:
            # Ищем по полю pdf
            query = self._db.collection('books').where('pdf', '==', pdf_path).limit(1)
            
            for doc in query.stream():
                return self._doc_to_book(doc.to_dict())
            
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска книги по PDF: {e}", exc_info=True)
            return None
    
    # ========== Analytics ==========
    
    def increment_view_count(self, book_id: int) -> bool:
        """
        Атомарно увеличивает счётчик просмотров.
        
        Args:
            book_id: ID книги
            
        Returns:
            True если успешно, иначе False
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return False
        
        try:
            doc_ref = self._db.collection('books').document(str(book_id))
            doc_ref.update({
                'viewCount': __import__('firebase_admin').firestore.Increment(1)
            })
            return True
        except Exception as e:
            logger.error(f"Ошибка увеличения просмотров: {e}", exc_info=True)
            return False
    
    def increment_download_count(self, book_id: int) -> bool:
        """
        Атомарно увеличивает счётчик скачиваний.
        
        Args:
            book_id: ID книги
            
        Returns:
            True если успешно, иначе False
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return False
        
        try:
            doc_ref = self._db.collection('books').document(str(book_id))
            doc_ref.update({
                'downloadCount': __import__('firebase_admin').firestore.Increment(1)
            })
            return True
        except Exception as e:
            logger.error(f"Ошибка увеличения скачиваний: {e}", exc_info=True)
            return False
    
    # ========== Bookmarks ==========
    
    def add_bookmark(self, bookmark: Bookmark) -> bool:
        """
        Добавляет закладку в Firestore.
        
        Args:
            bookmark: Bookmark объект
            
        Returns:
            True если успешно, иначе False
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return False
        
        try:
            doc_ref = self._db.collection('bookmarks').document()
            doc_ref.set({
                'id': doc_ref.id,
                'bookId': bookmark.book_id,
                'page': bookmark.page_number,
                'timestamp': bookmark.timestamp,
                'note': getattr(bookmark, 'note', '')
            })
            logger.info(f"Закладка добавлена для книги {bookmark.book_id}, страница {bookmark.page_number}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления закладки: {e}", exc_info=True)
            return False
    
    def get_bookmarks_by_book(self, book_id: int) -> List:
        """
        Получает все закладки для книги.
        
        Args:
            book_id: ID книги
            
        Returns:
            Список закладок
        """
        if not self._initialized:
            logger.warning("Firestore не инициализирован")
            return []
        
        try:
            bookmarks = []
            docs = self._db.collection('bookmarks').where('bookId', '==', book_id).order_by('page').stream()
            
            for doc in docs:
                data = doc.to_dict()
                bookmarks.append(self._doc_to_bookmark(data))
            
            return bookmarks
        except Exception as e:
            logger.error(f"Ошибка получения закладок: {e}", exc_info=True)
            return []
    
    # ========== Private Methods ==========
    
    def _doc_to_book(self, data: Dict[str, Any]) -> Book:
        """
        Конвертирует Firestore document в Book объект.
        """
        return Book(
            id=data.get('id', 0),
            title=data.get('title', ''),
            author=data.get('author', ''),
            category=data.get('category', ''),
            year=data.get('year', 0),
            description=data.get('description', ''),
            cover=data.get('cover', ''),
            pdf=data.get('pdf', ''),
            file_size=data.get('fileSize'),
            pages=data.get('pages'),
            copyright_protected=bool(data.get('copyrightProtected', False)),
            view_count=data.get('viewCount', 0),
            download_count=data.get('downloadCount', 0)
        )
    
    def _book_to_doc(self, book: Book) -> Dict[str, Any]:
        """
        Конвертирует Book объект в dict для Firestore.
        """
        return {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'year': book.year,
            'description': book.description,
            'cover': book.cover,
            'pdf': book.pdf,
            'fileSize': book.file_size,
            'pages': book.pages,
            'copyrightProtected': bool(book.copyright_protected),
            'viewCount': book.view_count,
            'downloadCount': book.download_count
        }
    
    def _doc_to_bookmark(self, data: Dict[str, Any]) -> Bookmark:
        """
        Конвертирует Firestore document в Bookmark объект.
        """
        return Bookmark(
            id=data.get('id', 0),
            book_id=data.get('bookId', 0),
            page_number=data.get('page', 0),
            timestamp=data.get('timestamp', '')
        )
    
    def _pdf_exists(self, pdf_path: str, exclude_id: int = None) -> bool:
        """
        Проверяет, существует ли уже PDF у другой книги.
        """
        try:
            query = self._db.collection('books').where('pdf', '==', pdf_path).limit(1)
            
            for doc in query.stream():
                data = doc.to_dict()
                if exclude_id and data.get('id') == exclude_id:
                    continue
                return True
            
            return False
        except Exception:
            return False


# Singleton instance
firestore_manager = FirestoreBookManager()
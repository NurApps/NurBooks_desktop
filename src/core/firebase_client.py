"""
Firebase Client для взаимодействия с Firebase Firestore.

PDF и обложки хранятся на GitHub Releases.
"""

from typing import Optional, List, Dict, Any
import src.config as config
from src.core.models import Book, Bookmark
from src.core.logger import get_logger

logger = get_logger(__name__)

class FirebaseClient:
    """Клиент для взаимодействия с Firebase Firestore."""
    
    def __init__(self):
        self._initialized = False
        self._db = None
        self._auth = None
        
        if config.FirebaseConfig.is_configured():
            self._initialize_firebase(config.FirebaseConfig.to_dict())
        else:
            logger.warning("Firebase не настроен. Используется режим Offline.")
    
    def _initialize_firebase(self, config_dict: Dict[str, Any]):
        """Инициализирует Firebase"""
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            if not firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
                cred = credentials.Certificate(config.FirebaseConfig.SERVICE_ACCOUNT_KEY_PATH)
                firebase_admin.initialize_app(cred, {
                    'projectId': config_dict['projectId']
                })
                logger.info("Firebase App инициализирован")
            
            self._db = firestore.client()
            self._initialized = True
            logger.info("Firebase Client инициализирован успешно")
        except firebase_admin.exceptions.AlreadyExistsError:
            logger.info("Firebase App уже инициализирован, повторное использование")
            self._db = firestore.client()
            self._initialized = True
        except Exception as e:
            logger.error(f"Ошибка инициализации Firebase: {e}", exc_info=True)
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирован ли Firebase"""
        return self._initialized
    
    # ============= Books =============
    
    def _doc_to_book(self, data: Dict[str, Any]) -> Book:
        """Конвертирует Firestore document в Book объект"""
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
        """Конвертирует Book объект в dict для Firestore"""
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
    
    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Получает книгу по ID из Firestore"""
        if not self._initialized or not self._db:
            return None
        try:
            doc = self._db.collection('books').document(str(book_id)).get()
            if doc.exists:
                return self._doc_to_book(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Ошибка получения книги {book_id}: {e}", exc_info=True)
            return None
    
    def get_all_books(self) -> List[Book]:
        """Получает все книги из Firestore"""
        if not self._initialized or not self._db:
            return []
        try:
            books = []
            for doc in self._db.collection('books').order_by('id').stream():
                books.append(self._doc_to_book(doc.to_dict()))
            return books
        except Exception as e:
            logger.error(f"Ошибка получения всех книг: {e}", exc_info=True)
            return []
    
    def search_books(self, query: str) -> List[Book]:
        """Поиск книг по названию или автору"""
        if not self._initialized or not self._db:
            return []
        try:
            books = []
            seen_ids = set()
            
            title_query = self._db.collection('books').where('title', '>=', query).where('title', '<=', query + 'z')
            for doc in title_query.stream():
                data = doc.to_dict()
                if data['id'] not in seen_ids:
                    books.append(self._doc_to_book(data))
                    seen_ids.add(data['id'])
            
            author_query = self._db.collection('books').where('author', '>=', query).where('author', '<=', query + 'z')
            for doc in author_query.stream():
                data = doc.to_dict()
                if data['id'] not in seen_ids:
                    books.append(self._doc_to_book(data))
                    seen_ids.add(data['id'])
            
            return books
        except Exception as e:
            logger.error(f"Ошибка поиска книг: {e}", exc_info=True)
            return []
    
    # ============= Analytics =============
    
    def increment_view_count(self, book_id: int) -> bool:
        """Атомарно увеличивает счётчик просмотров"""
        if not self._initialized or not self._db:
            return False
        try:
            import firebase_admin
            doc_ref = self._db.collection('books').document(str(book_id))
            doc_ref.update({'viewCount': firebase_admin.firestore.Increment(1)})
            return True
        except Exception as e:
            logger.error(f"Ошибка увеличения просмотров: {e}", exc_info=True)
            return False
    
    def increment_download_count(self, book_id: int) -> bool:
        """Атомарно увеличивает счётчик скачиваний"""
        if not self._initialized or not self._db:
            return False
        try:
            import firebase_admin
            doc_ref = self._db.collection('books').document(str(book_id))
            doc_ref.update({'downloadCount': firebase_admin.firestore.Increment(1)})
            return True
        except Exception as e:
            logger.error(f"Ошибка увеличения скачиваний: {e}", exc_info=True)
            return False
    
    def get_book_statistics(self, book_id: int) -> Dict[str, Any]:
        """Получает статистику по книге из Firestore"""
        if not self._initialized or not self._db:
            return {'view_count': 0, 'download_count': 0, 'view_to_download_ratio': 0}
        try:
            doc = self._db.collection('books').document(str(book_id)).get()
            if doc.exists:
                data = doc.to_dict()
                views = data.get('viewCount', 0)
                downloads = data.get('downloadCount', 0)
                ratio = downloads / views if views > 0 else 0
                return {'view_count': views, 'download_count': downloads, 'view_to_download_ratio': ratio}
            return {'view_count': 0, 'download_count': 0, 'view_to_download_ratio': 0}
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}", exc_info=True)
            return {'view_count': 0, 'download_count': 0, 'view_to_download_ratio': 0}
    
    # ============= Bookmarks =============
    
    def add_bookmark(self, bookmark: Bookmark) -> bool:
        """Добавляет закладку в Firestore"""
        if not self._initialized or not self._db:
            return False
        try:
            doc_ref = self._db.collection('bookmarks').document()
            doc_ref.set({
                'id': doc_ref.id,
                'bookId': bookmark.book_id,
                'page': bookmark.page_number,
                'timestamp': bookmark.timestamp
            })
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления закладки: {e}", exc_info=True)
            return False
    
    def get_bookmark_by_id(self, bookmark_id: int) -> Optional[Bookmark]:
        """Получает закладку по ID из Firestore"""
        if not self._initialized or not self._db:
            return None
        try:
            doc = self._db.collection('bookmarks').document(str(bookmark_id)).get()
            if doc.exists:
                data = doc.to_dict()
                return Bookmark(
                    id=data.get('id', 0),
                    book_id=data.get('bookId', 0),
                    page_number=data.get('page', 0),
                    timestamp=data.get('timestamp', '')
                )
            return None
        except Exception as e:
            logger.error(f"Ошибка получения закладки: {e}", exc_info=True)
            return None
    
    def get_bookmarks_by_book(self, book_id: int) -> List[Bookmark]:
        """Получает все закладки для книги из Firestore"""
        if not self._initialized or not self._db:
            return []
        try:
            bookmarks = []
            for doc in self._db.collection('bookmarks').where('bookId', '==', book_id).order_by('page').stream():
                data = doc.to_dict()
                bookmarks.append(Bookmark(
                    id=data.get('id', 0),
                    book_id=data.get('bookId', 0),
                    page_number=data.get('page', 0),
                    timestamp=data.get('timestamp', '')
                ))
            return bookmarks
        except Exception as e:
            logger.error(f"Ошибка получения закладок: {e}", exc_info=True)
            return []
    
    def delete_bookmark(self, bookmark_id) -> bool:
        """Удаляет закладку из Firestore"""
        if not self._initialized or not self._db:
            return False
        try:
            self._db.collection('bookmarks').document(str(bookmark_id)).delete()
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления закладки {bookmark_id}: {e}", exc_info=True)
            return False
    
    def get_all_bookmarks_with_books(self) -> List:
        """Получает все закладки с книгами из Firestore"""
        if not self._initialized or not self._db:
            return []
        try:
            result = []
            books_cache = {}
            for doc in self._db.collection('bookmarks').order_by('timestamp', direction='DESCENDING').stream():
                data = doc.to_dict()
                bookmark = Bookmark(
                    id=data.get('id', 0),
                    book_id=data.get('bookId', 0),
                    page_number=data.get('page', 0),
                    timestamp=data.get('timestamp', '')
                )
                bid = data.get('bookId')
                if bid not in books_cache:
                    books_cache[bid] = self.get_book_by_id(bid)
                book = books_cache.get(bid)
                if book:
                    result.append((bookmark, book))
            return result
        except Exception as e:
            logger.error(f"Ошибка получения закладок с книгами: {e}", exc_info=True)
            return []
    
    # ============= Reading Progress =============
    
    def save_reading_progress(self, book_id: int, page_number: int) -> bool:
        """Сохраняет прогресс чтения в Firestore"""
        if not self._initialized or not self._db:
            return False
        try:
            from datetime import datetime
            self._db.collection('reading_progress').document(str(book_id)).set({
                'bookId': book_id,
                'page': page_number,
                'timestamp': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения прогресса: {e}", exc_info=True)
            return False
    
    def get_reading_progress(self, book_id: int) -> int:
        """Получает прогресс чтения из Firestore"""
        if not self._initialized or not self._db:
            return 0
        try:
            doc = self._db.collection('reading_progress').document(str(book_id)).get()
            if doc.exists:
                return doc.to_dict().get('page', 0)
            return 0
        except Exception as e:
            logger.error(f"Ошибка получения прогресса: {e}", exc_info=True)
            return 0
    
    def get_all_reading_progress(self) -> dict:
        """Возвращает {book_id: page_number} для всех книг с прогрессом"""
        if not self._initialized or not self._db:
            return {}
        try:
            result = {}
            for doc in self._db.collection('reading_progress').order_by('timestamp', direction='DESCENDING').stream():
                data = doc.to_dict()
                result[data.get('bookId')] = data.get('page', 0)
            return result
        except Exception as e:
            logger.error(f"Ошибка получения всего прогресса: {e}", exc_info=True)
            return {}
    
    # ============= Book CRUD =============
    
    def add_book(self, book: Book) -> str:
        """Добавляет книгу в Firestore"""
        if not self._initialized or not self._db:
            return "error"
        try:
            if self.get_book_by_id(book.id):
                return "id_exists"
            self._db.collection('books').document(str(book.id)).set(self._book_to_doc(book))
            return "success"
        except Exception as e:
            logger.error(f"Ошибка добавления книги: {e}", exc_info=True)
            return "error"
    
    def update_book(self, book: Book) -> bool:
        """Обновляет книгу в Firestore"""
        if not self._initialized or not self._db:
            return False
        try:
            self._db.collection('books').document(str(book.id)).set(self._book_to_doc(book))
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления книги: {e}", exc_info=True)
            return False
    
    def delete_book(self, book_id: int) -> bool:
        """Удаляет книгу из Firestore"""
        if not self._initialized or not self._db:
            return False
        try:
            self._db.collection('books').document(str(book_id)).delete()
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления книги: {e}", exc_info=True)
            return False
    
    def clear_books(self) -> bool:
        """Очищает все книги из Firestore"""
        if not self._initialized or not self._db:
            return False
        try:
            for doc in self._db.collection('books').stream():
                doc.reference.delete()
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки книг: {e}", exc_info=True)
            return False
    
    def get_book_by_pdf(self, pdf_path: str):
        """Ищет книгу по пути PDF в Firestore"""
        if not self._initialized or not self._db:
            return None
        try:
            docs = self._db.collection('books').where('pdf', '==', pdf_path).limit(1).stream()
            for doc in docs:
                return self._doc_to_book(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска книги по PDF: {e}", exc_info=True)
            return None
    
    # ============= Analytics Events =============

    def log_analytics_event(self, event_type: str, book_id: int, metadata: Dict[str, Any] = None) -> bool:
        """Логирует событие аналитики в Firestore коллекцию analytics_events"""
        if not self._initialized or not self._db:
            return False
        try:
            from datetime import datetime
            event_data = {
                'eventType': event_type,
                'bookId': book_id,
                'timestamp': datetime.now().isoformat()
            }
            if metadata:
                event_data.update(metadata)
            self._db.collection('analytics_events').add(event_data)
            return True
        except Exception as e:
            logger.error(f"Ошибка логирования события {event_type}: {e}", exc_info=True)
            return False

    def get_book_analytics(self, book_id: int) -> Dict[str, Any]:
        """Получает агрегированную аналитику по книге из Firestore"""
        if not self._initialized or not self._db:
            return {}
        try:
            events = self._db.collection('analytics_events').where('bookId', '==', book_id).stream()
            views = 0
            downloads = 0
            for doc in events:
                data = doc.to_dict()
                if data.get('eventType') == 'view':
                    views += 1
                elif data.get('eventType') == 'download':
                    downloads += 1
            return {'views': views, 'downloads': downloads}
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}", exc_info=True)
            return {}

    # ============= Auth =============
    
    def sign_in_anonymous(self) -> Optional[str]:
        """Входит как anonymous user через Firebase Auth"""
        if not self._initialized:
            return None
        try:
            import firebase_admin
            from firebase_admin import auth
            user = auth.create_user()
            return user.uid
        except Exception as e:
            logger.error(f"Ошибка анонимного входа: {e}", exc_info=True)
            return None
    
    def sign_in_with_email(self, email: str, password: str) -> Optional[str]:
        """Входит по email/password"""
        if not self._initialized:
            return None
        try:
            import firebase_admin
            from firebase_admin import auth
            users = auth.list_users(filter=f'email:{email}')
            for user in users:
                return user.uid
            return None
        except Exception as e:
            logger.error(f"Ошибка входа по email: {e}", exc_info=True)
            return None
    
    def sign_out(self) -> bool:
        """Выходит из системы"""
        return True
    
    # ============= Account Info =============
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Получает информацию о текущем пользователе"""
        if not self._initialized:
            return None
        try:
            import firebase_admin
            from firebase_admin import auth
            current = auth.get_user_by_uid(firebase_admin.auth.get_current_user().uid) if hasattr(firebase_admin.auth, 'get_current_user') else None
            if current:
                return {
                    'uid': current.uid,
                    'email': current.email,
                    'display_name': current.display_name,
                    'phone_number': current.phone_number
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}", exc_info=True)
            return None


# Singleton instance для удобства
firebase_client = FirebaseClient()

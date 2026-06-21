"""
Модуль для отслеживания статистики (просмотров, скачиваний) и облачного хранения
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.core.models import Book
from src.core.logger import get_logger
from src.config import DEFAULT_DATA_PATH

logger = get_logger(__name__)


class Analytics:
    """
    Класс для отслеживания статистики просмотров и скачиваний
    """
    def __init__(self):
        self.data_path = DEFAULT_DATA_PATH
        self.db_path = os.path.join(self.data_path, "analytics.db")
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных аналитики"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица просмотров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        ''')
        
        # Таблица скачиваний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL,
                file_size TEXT,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        ''')
        
        # Таблица пользователей для приватности
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
        ''')
        
        # Таблица сессий для JWT
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                valid_until TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица настроек облачного хранилища
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cloud_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_token TEXT,
                account_id TEXT,
                bucket_name TEXT,
                enabled INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Таблица для логов ошибок (приватные данные)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                trace TEXT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT
            )
        ''')
        
        # Индексы для ускорения
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_views_book_id ON views(book_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_views_timestamp ON views(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_book_id ON downloads(book_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_timestamp ON downloads(timestamp)')
        
        conn.commit()
        conn.close()
    
    def log_view(self, book_id: int, user_id: Optional[str] = None, 
                 ip_address: Optional[str] = None) -> bool:
        """Записывает факт просмотра книги"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO views (book_id, user_id, ip_address, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (book_id, user_id, ip_address, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка записи просмотра: {e}", exc_info=True)
            return False
    
    def log_download(self, book_id: int, file_size: Optional[str] = None,
                     user_id: Optional[str] = None, ip_address: Optional[str] = None) -> bool:
        """Записывает факт скачивания книги"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO downloads (book_id, user_id, ip_address, timestamp, file_size)
                VALUES (?, ?, ?, ?, ?)
            ''', (book_id, user_id, ip_address, datetime.now().isoformat(), file_size))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка записи скачивания: {e}", exc_info=True)
            return False
    
    def get_views_count(self, book_id: int) -> int:
        """Получает количество просмотров книги"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM views WHERE book_id = ?', (book_id,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка получения количества просмотров: {e}", exc_info=True)
            return 0
    
    def get_downloads_count(self, book_id: int) -> int:
        """Получает количество скачиваний книги"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM downloads WHERE book_id = ?', (book_id,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка получения количества скачиваний: {e}", exc_info=True)
            return 0
    
    def get_book_statistics(self, book_id: int) -> Dict[str, Any]:
        """Получает статистику по книге"""
        views = self.get_views_count(book_id)
        downloads = self.get_downloads_count(book_id)
        
        return {
            'book_id': book_id,
            'views': views,
            'downloads': downloads,
            'view_to_download_ratio': downloads / views if views > 0 else 0
        }
    
    def save_cloud_settings(self, api_token: str, account_id: str, 
                           bucket_name: str, enabled: bool = False) -> bool:
        """Сохраняет настройки облачного хранилища"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cloud_settings (api_token, account_id, bucket_name, enabled, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (api_token, account_id, bucket_name, 1 if enabled else 0, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек облака: {e}", exc_info=True)
            return False
    
    def get_cloud_settings(self) -> Dict[str, Any]:
        """Получает настройки облачного хранилища"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM cloud_settings ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'api_token': row[1],
                    'account_id': row[2],
                    'bucket_name': row[3],
                    'enabled': bool(row[4])
                }
            return {}
        except Exception as e:
            logger.error(f"Ошибка получения настроек облака: {e}", exc_info=True)
            return {}
    
    def user_exists(self, username: str) -> bool:
        """Проверяет, существует ли пользователь"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя: {e}", exc_info=True)
            return False
    
    def create_user(self, username: str, password_hash: str, 
                   email: Optional[str] = None, is_admin: bool = False) -> bool:
        """Создает нового пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, created_at, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, datetime.now().isoformat(), 1 if is_admin else 0))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}", exc_info=True)
            return False
    
    def verify_user(self, username: str, password_hash: str) -> Optional[int]:
        """Проверяет учетные данные пользователя и возвращает user_id"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', 
                          (username, password_hash))
            row = cursor.fetchone()
            
            conn.close()
            
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя: {e}", exc_info=True)
            return None
    
    def create_session(self, user_id: int, token: str, valid_until: str,
                      ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """Создает сессию пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sessions (user_id, token, valid_until, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, token, valid_until, ip_address, user_agent))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
        except Exception as e:
            logger.error(f"Ошибка создания сессии: {e}", exc_info=True)
            return False
    
    def validate_session(self, token: str) -> bool:
        """Проверяет валидность сессии"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            cursor.execute('SELECT id FROM sessions WHERE token = ? AND valid_until > ?', 
                          (token, now))
            row = cursor.fetchone()
            
            conn.close()
            return row is not None
        except Exception as e:
            logger.error(f"Ошибка проверки сессии: {e}", exc_info=True)
            return False
    
    def cleanup_expired_sessions(self) -> bool:
        """Удаляет истекшие сессии"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            cursor.execute('DELETE FROM sessions WHERE valid_until < ?', (now,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки сессий: {e}", exc_info=True)
            return False
"""
Модуль для отслеживания статистики (просмотров, скачиваний)
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
from src.core.logger import get_logger
from src.config import DEFAULT_DATA_PATH

logger = get_logger(__name__)


class Analytics:
    def __init__(self):
        self.data_path = DEFAULT_DATA_PATH
        self.db_path = os.path.join(self.data_path, "analytics.db")
        self.init_db()
    
    def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL,
                file_size TEXT
            )
        ''')
        
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
        views = self.get_views_count(book_id)
        downloads = self.get_downloads_count(book_id)
        return {
            'book_id': book_id,
            'views': views,
            'downloads': downloads,
            'view_to_download_ratio': downloads / views if views > 0 else 0
        }
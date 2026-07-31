"""Инициализация core-модуля"""
from src.core.analytics import Analytics
from src.core.database import Database
from src.core.downloader import Downloader
from src.core.firebase_client import FirebaseClient, firebase_client
from src.core.logger import get_logger, logger
from src.core.models import Author, Book, Bookmark, Notification, UserSettings
from src.core.notifications import NotificationManager
from src.core.statistics_manager import StatisticsManager, stats
from src.core.storage import Storage

__all__ = [
    'Book',
    'Author',
    'UserSettings',
    'Notification',
    'Bookmark',
    'Database',
    'Analytics',
    'StatisticsManager',
    'stats',  # Singleton instance
    'FirebaseClient',
    'firebase_client',  # Singleton instance
    'Downloader',
    'NotificationManager',
    'Storage',
    'get_logger',
    'logger',
]


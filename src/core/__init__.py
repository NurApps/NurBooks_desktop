"""Инициализация core-модуля"""
from src.core.models import Book, Author, UserSettings, Notification, Bookmark
from src.core.database import Database
from src.core.analytics import Analytics
from src.core.statistics_manager import StatisticsManager, stats
from src.core.firebase_client import FirebaseClient, firebase_client
from src.core.downloader import Downloader
from src.core.notifications import NotificationManager
from src.core.storage import Storage
from src.core.logger import get_logger, logger

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


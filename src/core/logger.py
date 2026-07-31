"""
Модуль логгирования для NurBooks
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_log_directory() -> str:
    """
    Возвращает директорию для хранения логов.
    В зависимости от окружения:
    - Для EXE: папка logs рядом с executable
    - Для разработки: папка logs в корне проекта
    """
    if getattr(sys, 'frozen', False):
        # Запущено как EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # Запущено из исходного кода
        base_path = Path(__file__).parent.parent.parent

    log_dir = os.path.join(base_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logger(
    name: str = "NurBooks",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """
    Настраивает и возвращает логгер с указанным именем.

    Args:
        name: Имя логгера (обычно __name__ модуля)
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Писать логи в файл
        log_to_console: Выводить логи в консоль
        max_bytes: Максимальный размер одного файла лога (байты)
        backup_count: Количество хранимых файлов логов

    Returns:
        Настроенный экземпляр logging.Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Формат сообщений
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Если логгер уже настроен, не настраиваем повторно
    if logger.handlers:
        return logger

    # Файловый обработчик с ротацией
    if log_to_file:
        try:
            log_dir = get_log_directory()
            log_file = os.path.join(log_dir, f"{name}.log")

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Если не удалось создать файл логов, пишем в консоль
            print(f"Не удалось создать файл логов: {e}")

    # Консольный обработчик
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Обработка необработанных исключений
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        logger.critical(
            "Необработанное исключение",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception

    return logger


# Глобальный логгер по умолчанию
logger = setup_logger()


def get_logger(name: str = None) -> logging.Logger:
    """
    Получает логгер с указанным именем.

    Args:
        name: Имя логгера. Если None, возвращает логгер по умолчанию.

    Returns:
        Экземпляр logging.Logger
    """
    if name is None:
        return logger
    return setup_logger(name)


# Уровни логирования для удобного импорта
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

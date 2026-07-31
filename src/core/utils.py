import hashlib


def format_file_size(size_bytes: int) -> str:
    """Форматирует размер файла в читаемый вид"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"

def safe_filename(filename: str) -> str:
    """Очищает имя файла от небезопасных символов"""
    keep_chars = (' ', '.', '_', '-')
    return "".join(c for c in filename if c.isalnum() or c in keep_chars).rstrip()

def get_file_hash(filepath: str) -> str:
    """Вычисляет хеш файла для проверки целостности"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return ""

def validate_pdf(filepath: str) -> bool:
    """Проверяет, является ли файл валидным PDF"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    except OSError:
        return False

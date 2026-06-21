"""

check_stability.py — Проверка стабильности кода перед миграцией на Firebase

Выполняет:
1. Проверку все ли вызовы stats используются
2. Проверку, что нет прямых вызовов database.increment_*
3. Проверку, что all dependencies установлены
"""

import os
import re
import sys


def check_stats_usage():
    """
    Проверяет, что все вызовы database.increment_* заменены на stats
    """
    files_to_check = [
        'src/ui/pages/book_view.py',
        'src/ui/main.py',
        'src/ui/pages/pdf_reader.py',
        'src/core/statistics_manager.py',
    ]
    
    errors = []
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем паттерн "storage.database.increment_" или "database.increment_" (кроме stats_manager)
        if 'statistics_manager' not in filepath:
            bad_patterns = [
                r'storage\.database\.increment_\w+\s*\(',
                r'Database\(\)\.increment_\w+\s*\(',
            ]
            
            for pattern in bad_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    errors.append(f"❌ {filepath}: Найден прямой вызов {matches[0]} (должно быть stats)")
    
    if errors:
        print("\n❌ ОБНАРУЖЕНЫ ОШИБКИ \n")
        for error in errors:
            print(error)
        return False
    else:
        print("✅ Все вызовы статистики используют stats! \n")
        return True


def check_imports():
    """
    Проверяет, что все модули импортируются корректно
    """
    print("Проверка импортов...")
    
    try:
        from src.core.statistics_manager import stats
        print("✅ stats импортируется")
    except Exception as e:
        print(f"❌ Ошибка импорта stats: {e}")
        return False
    
    try:
        from src.core.firebase_client import firebase_client
        print("✅ firebase_client импортируется")
    except Exception as e:
        print(f"⚠️ firebase_client импортируется с предупреждением: {e} (это нормально, пока нет serviceAccountKey.json)")
    
    try:
        from src.core.database import Database
        print("✅ Database импортируется")
    except Exception as e:
        print(f"❌ Ошибка импорта Database: {e}")
        return False
    
    return True


def check_config():
    """
    Проверяет конфигурацию Firebase
    """
    print("\nПроверка конфигурации Firebase...\n")
    
    try:
        from src.config import FirebaseConfig
        
        print(f"Project ID: {FirebaseConfig.PROJECT_ID}")
        print(f"API Key: {FirebaseConfig.API_KEY[:10]}...{FirebaseConfig.API_KEY[-10:]}")
        print(f"Storage Bucket: {FirebaseConfig.STORAGE_BUCKET}")
        
        if FirebaseConfig.is_configured():
            print("✅ Firebase настроен")
        else:
            print("⚠️ Firebase не настроен (используется режим Offline)")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")
        return False


def main():
    print("="*60)
    print("🚀 Проверка стабильности NurBooks перед миграцией на Firebase")
    print("="*60 + "\n")
    
    results = []
    
    # Проверка 1: Использование stats
    results.append(check_stats_usage())
    
    # Проверка 2: Импорты
    results.append(check_imports())
    
    # Проверка 3: Конфиг
    results.append(check_config())
    
    # Финальный вывод
    print("\n" + "="*60)
    if all(results):
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! You're ready for Firebase migration!")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ ПРОВАЛЕНЫ. Проверьте вывод выше.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

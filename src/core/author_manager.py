import json
import os

from src.config import DEFAULT_DATA_PATH
from src.core.models import Author


class AuthorManager:
    def __init__(self):
        self.data_path = DEFAULT_DATA_PATH
        self.authors_file_path = os.path.join(self.data_path, "authors.json")

    def load_authors(self) -> list[Author]:
        """Загружает авторов. Сначала пробует API, затем локальный JSON"""
        try:
            from src.core.firebase_client import firebase_client
            if firebase_client.is_initialized():
                data = firebase_client.get_all_authors()
                if data:
                    authors = [Author(**a) for a in data]
                    self.save_authors_local(authors)
                    return authors
        except Exception:
            pass
        return self.load_authors_local()

    def load_authors_local(self) -> list[Author]:
        """Загружает авторов из локального JSON"""
        try:
            if not os.path.exists(self.authors_file_path):
                return []

            with open(self.authors_file_path, encoding="utf-8") as f:
                data = json.load(f)
                return [Author(**author_data) for author_data in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        except Exception as e:
            print(f"Ошибка загрузки авторов: {e}")
            return []

    def save_authors(self, authors: list[Author]):
        """Сохраняет авторов. Сначала в API, затем локально"""
        try:
            from src.core.firebase_client import firebase_client
            if firebase_client.is_initialized():
                firebase_client.save_authors([a.to_dict() for a in authors])
        except Exception:
            pass
        self.save_authors_local(authors)

    def save_authors_local(self, authors: list[Author]):
        """Сохраняет авторов в локальный JSON"""
        try:
            os.makedirs(self.data_path, exist_ok=True)
            with open(self.authors_file_path, "w", encoding="utf-8") as f:
                json.dump([author.to_dict() for author in authors], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения авторов: {e}")

    def get_author_by_id(self, author_id: int) -> Author | None:
        """Получает автора по ID"""
        authors = self.load_authors()
        for author in authors:
            if author.id == author_id:
                return author
        return None

    def get_author_by_name(self, name: str) -> Author | None:
        """Получает автора по имени"""
        authors = self.load_authors()
        for author in authors:
            if author.name.lower() == name.lower():
                return author
        return None

    def add_author(self, author: Author) -> bool:
        """Добавляет нового автора"""
        try:
            authors = self.load_authors()

            # Проверяем, существует ли уже автор с таким ID
            for existing_author in authors:
                if existing_author.id == author.id:
                    return False  # Автор с таким ID уже существует

            authors.append(author)
            self.save_authors(authors)
            return True
        except Exception as e:
            print(f"Ошибка добавления автора: {e}")
            return False

    def update_author(self, updated_author: Author) -> bool:
        """Обновляет информацию об авторе"""
        try:
            authors = self.load_authors()
            updated = False

            for i, author in enumerate(authors):
                if author.id == updated_author.id:
                    authors[i] = updated_author
                    updated = True
                    break

            if updated:
                self.save_authors(authors)

            return updated
        except Exception as e:
            print(f"Ошибка обновления автора: {e}")
            return False

    def delete_author(self, author_id: int) -> bool:
        """Удаляет автора по ID"""
        try:
            authors = self.load_authors()
            original_length = len(authors)

            authors = [author for author in authors if author.id != author_id]

            if len(authors) < original_length:
                self.save_authors(authors)
                return True
            else:
                return False  # Автор с указанным ID не найден
        except Exception as e:
            print(f"Ошибка удаления автора: {e}")
            return False

    def get_or_create_author(self, name: str, bio: str = "") -> Author:
        """Получает автора по имени или создает нового, если не существует"""
        author = self.get_author_by_name(name)
        if author:
            return author

        # Генерируем новый ID
        authors = self.load_authors()
        new_id = max([author.id for author in authors], default=0) + 1

        new_author = Author(id=new_id, name=name, bio=bio, books=[])
        self.add_author(new_author)
        return new_author

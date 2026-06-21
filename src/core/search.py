from typing import List
from src.core.models import Book

class SearchEngine:
    def __init__(self, books: List[Book]):
        self.books = books
    
    def search_books(self, query: str, category: str = None, author: str = None) -> List[Book]:
        """Поиск книг по запросу с фильтрацией"""
        results = self.books
        
        if query:
            query = query.lower()
            results = [
                book for book in results
                if query in book.title.lower() or 
                   query in book.author.lower() or
                   query in book.description.lower() or
                   query in book.category.lower()
            ]
        
        if category and category != "Все категории":
            results = [book for book in results if book.category == category]
        
        if author and author != "Все авторы":
            results = [book for book in results if book.author == author]
        
        return results
    
    def get_categories(self) -> List[str]:
        """Получить список всех категорий"""
        categories = list(set(book.category for book in self.books))
        return ["Все категории"] + sorted(categories)
    
    def get_authors(self) -> List[str]:
        """Получить список всех авторов"""
        authors = list(set(book.author for book in self.books))
        return ["Все авторы"] + sorted(authors) 
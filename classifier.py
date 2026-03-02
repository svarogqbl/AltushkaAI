# classifier.py

SEARCH_KEYWORDS = [
    "погода", "новости", "курс", "цена", "сколько стоит",
    "кто выиграл", "кто победил", "последний", "текущий",
    "сегодня", "вчера", "на этой неделе", "в 2025", "в 2024", "в 2026",
    "актуальный", "последняя версия", "изменился", "случилось",
    "найди", "покажи", "гугл", "интернет"
]

def needs_search_simple(query: str) -> tuple[bool, str]:
    """Быстрое определение необходимости поиска"""
    query_lower = query.lower().strip()
    
    for keyword in SEARCH_KEYWORDS:
        if keyword in query_lower:
            return True, query
    
    if "?" in query and len(query) < 100:
        if any(word in query_lower for word in ["что", "кто", "где", "когда", "как"]):
            personal_words = ["меня", "моё", "моя", "мой", "нам", "наш", "тебя", "твоё", "ты", "твои"]
            if not any(word in query_lower for word in personal_words):
                return True, query
    
    return False, None
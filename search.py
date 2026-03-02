import aiohttp
from config import SEARXNG_URL, SEARCH_MAX_RESULTS, SEARCH_TIMEOUT

async def search_searxng(query: str, max_results: int = None, categories: str = "general") -> str:
    """
    Ищет информацию через SearXNG.
    
    Args:
        query: Поисковый запрос
        max_results: Максимальное количество результатов
        categories: Категория (general, news, it, science, weather)
    
    Returns:
        Строка с отформатированными результатами
    """
    if max_results is None:
        max_results = SEARCH_MAX_RESULTS
    
    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
        "language": "ru-RU",
        "categories": categories,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                SEARXNG_URL, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=SEARCH_TIMEOUT)
            ) as response:
                if response.status != 200:
                    return f"❌ Ошибка API: статус {response.status}"
                
                data = await response.json()
                results = data.get("results", [])[:max_results]
                
                if not results:
                    return "🔍 Ничего не найдено по этому запросу."
                
                context = f"📡 Результаты поиска по запросу «{query}»:\n\n"
                for i, r in enumerate(results, 1):
                    title = r.get("title", "Без названия")
                    content = r.get("content", "")[:200]
                    url = r.get("url", "")
                    source = r.get("source", "неизвестный источник")
                    
                    context += f"{i}. [{title}]({url})\n"
                    if content:
                        context += f"   {content}...\n"
                    context += f"   🔗 Источник: {source}\n\n"
                
                return context
                
    except aiohttp.ClientError as e:
        return f"🌐 Ошибка соединения: {e}"
    except Exception as e:
        return f"❌ Ошибка поиска: {type(e).__name__}: {e}"


async def search_news(query: str, max_results: int = 3) -> str:
    """Поиск только новостей"""
    return await search_searxng(query, max_results, categories="news")


async def search_it(query: str, max_results: int = 3) -> str:
    """Поиск IT-статей"""
    return await search_searxng(query, max_results, categories="it")
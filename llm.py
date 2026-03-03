import aiohttp
from config import LM_STUDIO_URL

async def get_llm_response(messages: list, temperature: float = 0.7) -> str:
    """Отправляет запрос к LM Studio и получает ответ"""
    headers = {"Content-Type": "application/json"}
    
    data = {
        "model": "local-model",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": -1,
        "stream": False
    }

    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"📤 Отправляю в LLM {len(messages)} сообщений:")
    for i, msg in enumerate(messages[-5:], 1):  # Последние 5
        logger.debug(f"  {i}. [{msg['role']}] {msg['content'][:100]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LM_STUDIO_URL, 
                json=data, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"❌ Ошибка LLM API: статус {response.status}"
    except Exception as e:
        return f"❌ Ошибка связи с LM Studio: {e}"


async def create_summary(messages_text: str) -> str:
    """Создаёт краткое резюме из текста переписки"""
    prompt = f"""Резюмируй диалог в 2-3 предложениях (факты, имена, темы):
{messages_text[:2000]}
Резюме:"""
    
    messages = [{"role": "user", "content": prompt}]
    response = await get_llm_response(messages, temperature=0.3)
    return response.strip()
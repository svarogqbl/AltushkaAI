# =============================================================================
# BOT.PY — Telegram-бот AltushkaAI
# =============================================================================

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Импорт наших модулей
from config import BOT_TOKEN
from database import init_db, get_history, add_message, clear_history, save_fact, get_facts
from search import search_searxng
from llm import get_llm_response
from classifier import needs_search_simple

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройка логирования
logging.basicConfig(level=logging.INFO)


# =============================================================================
# ОБРАБОТЧИКИ КОМАНД
# =============================================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start — начало диалога"""
    user_id = message.from_user.id
    clear_history(user_id)
    await message.answer(
        "Привет! Я Альтушка, твой персональный ИИ-помощник! ✨\n\n"
        "Что я умею:\n"
        "• Отвечать на вопросы\n"
        "• Искать информацию в интернете (/find)\n"
        "• Запоминать факты о тебе (/set_fact)\n"
        "• Очищать историю (/clear)\n\n"
        "Напиши мне что-нибудь! 😊"
    )


@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Команда /clear — очистка истории"""
    user_id = message.from_user.id
    clear_history(user_id)
    await message.answer("🧹 История переписки очищена. Начнём с чистого листа!")


@dp.message(Command("find"))
async def cmd_search(message: types.Message):
    """Команда /find — поиск в интернете"""
    user_id = message.from_user.id
    query = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    if not query:
        await message.answer("🔍 Что найти? Пример: /find погода Москва")
        return
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    status_msg = await message.answer("🔎 Ищу информацию в интернете...")
    
    try:
        search_results = await search_searxng(query, max_results=4)
        
        system_context = f"""Ты Альтушка. Вот информация по запросу "{query}":
{search_results}
Ответь кратко и по-дружески."""
        
        history = get_history(user_id)
        history.append({"role": "system", "content": system_context})
        history.append({"role": "user", "content": query})
        
        ai_response = await get_llm_response(history)
        
        add_message(user_id, "user", query, auto_summary=True)
        add_message(user_id, "assistant", ai_response, auto_summary=False)
        
        await status_msg.edit_text(ai_response)
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")


@dp.message(Command("set_fact"))
async def cmd_set_fact(message: types.Message):
    """Команда /set_fact — запомнить факт"""
    user_id = message.from_user.id
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        await message.answer("Используй: /set_fact <ключ> <значение>")
        return
    
    key, value = args[1], args[2]
    save_fact(user_id, key, value)
    await message.answer(f"✅ Запомнила: {key} = {value}")


@dp.message()
async def chat_handler(message: types.Message):
    """Обычные сообщения — чат с ботом"""
    user_id = message.from_user.id
    user_text = message.text
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # 1. Загружаем ТЕКУЩУЮ историю (без нового сообщения!)
        history = get_history(user_id)
        
        # 2. Определяем, нужен ли поиск
        needs_search, search_query = needs_search_simple(user_text)
        
        if needs_search:
            status_msg = await message.answer(f"🔎 Ищу: {search_query}...")
            search_results = await search_searxng(search_query, max_results=4)
            
            # Добавляем результаты поиска В КОНТЕКСТ (но не в базу!)
            history.append({"role": "system", "content": f"🌐 Поиск: {search_results}"})
        
        # 3. ДОБАВЛЯЕМ сообщение пользователя В ИСТОРИЮ (только здесь!)
        history.append({"role": "user", "content": user_text})
        
        # 4. Запрос к LLM
        ai_response = await get_llm_response(history)
        
        # 5. СОХРАНЯЕМ оба сообщения в базу (пользователь + ответ)
        add_message(user_id, "user", user_text, auto_summary=True)
        add_message(user_id, "assistant", ai_response, auto_summary=False)
        
        # 6. Отправляем ответ
        if needs_search:
            await status_msg.edit_text(ai_response)
        else:
            await message.answer(ai_response)
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# =============================================================================
# ЗАПУСК
# =============================================================================

async def main():
    """Точка входа"""
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот выключен")
# =============================================================================
# DATABASE.PY — Работа с SQLite (память бота + автоматические резюме)
# =============================================================================

import sqlite3
import json
import asyncio
from datetime import datetime
from config import (
    DB_PATH,
    MAX_HISTORY_MESSAGES,
    SUMMARY_THRESHOLD,
    KEEP_RECENT_MESSAGES,
    MAX_SUMMARIES_COUNT
)

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# =============================================================================

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            facts_json TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            summary_text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            message_range TEXT
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON messages(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_summaries ON summaries(user_id)")
    
    conn.commit()
    conn.close()


# =============================================================================
# РАБОТА С ИСТОРИЕЙ
# =============================================================================

def get_history(user_id, limit=None):
    """Загружает историю пользователя с учётом резюме"""
    if limit is None:
        limit = MAX_HISTORY_MESSAGES
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    system_prompt = [{
        "role": "system",
        "content": """Ты Альтушка, дружелюбная девушка-помощник.
Ты общаешься на "ты", используешь эмодзи ✨, поддерживаешь пользователя.
Отвечай кратко, но с душой. Никогда не показывай свои мысли или тег <think>."""
    }]
    
    cursor.execute("""
        SELECT summary_text FROM summaries 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, MAX_SUMMARIES_COUNT))
    
    summaries = []
    for row in cursor.fetchall():
        summaries.append({
            "role": "system",
            "content": f"📚 Контекст из прошлого диалога: {row[0]}"
        })
    
    cursor.execute("""
        SELECT role, content FROM messages 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (user_id, limit))
    
    messages = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
    conn.close()
    
    return system_prompt + summaries[::-1] + messages[::-1]


def get_message_count(user_id):
    """Возвращает количество сообщений пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_old_messages_for_summary(user_id, keep_count=KEEP_RECENT_MESSAGES):
    """Возвращает старые сообщения для создания резюме"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM messages 
        WHERE user_id = ? 
        ORDER BY timestamp ASC
    """, (user_id,))
    all_messages = cursor.fetchall()
    conn.close()
    
    if len(all_messages) > keep_count:
        return all_messages[:-keep_count]
    return []


def add_message(user_id, role, content, auto_summary=True):
    """Добавляет сообщение в базу"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()
    
    if auto_summary:
        # Запускаем создание резюме в фоне (не блокируем бота)
        asyncio.create_task(check_and_create_summary_async(user_id))


def clear_history(user_id):
    """Очищает историю пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM summaries WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# =============================================================================
# АВТОМАТИЧЕСКОЕ СОЗДАНИЕ РЕЗЮМЕ (ASYNC Версия)
# =============================================================================

async def check_and_create_summary_async(user_id):
    """Асинхронная версия проверки и создания резюме"""
    count = get_message_count(user_id)
    
    if count < SUMMARY_THRESHOLD:
        return
    
    old_messages = get_old_messages_for_summary(user_id, keep_count=KEEP_RECENT_MESSAGES)
    
    if len(old_messages) < 10:
        return
    
    try:
        from llm import create_summary
    except ImportError:
        return
    
    messages_text = "\n".join([f"{role}: {content}" for role, content in old_messages[:40]])
    
    try:
        summary = await create_summary(messages_text)
    except Exception as e:
        print(f"⚠️ Ошибка создания резюме: {e}")
        return
    
    save_summary(user_id, summary, f"1-{len(old_messages)}")
    delete_old_messages(user_id, keep_count=KEEP_RECENT_MESSAGES)
    delete_old_summaries(user_id, keep_count=MAX_SUMMARIES_COUNT)
    
    print(f"✅ Резюме создано для пользователя {user_id}")


# =============================================================================
# СОХРАНЕНИЕ РЕЗЮМЕ
# =============================================================================

def save_summary(user_id, summary_text, message_range="auto"):
    """Сохраняет резюме в базу"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO summaries (user_id, summary_text, message_range) 
        VALUES (?, ?, ?)
    """, (user_id, summary_text, message_range))
    conn.commit()
    conn.close()


def delete_old_summaries(user_id, keep_count=MAX_SUMMARIES_COUNT):
    """Удаляет старые резюме"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM summaries 
        WHERE user_id = ? 
        AND id NOT IN (
            SELECT id FROM summaries 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        )
    """, (user_id, user_id, keep_count))
    conn.commit()
    conn.close()


def delete_old_messages(user_id, keep_count=KEEP_RECENT_MESSAGES):
    """Удаляет старые сообщения"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM messages 
        WHERE user_id = ? 
        AND id NOT IN (
            SELECT id FROM messages 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        )
    """, (user_id, user_id, keep_count))
    conn.commit()
    conn.close()


# =============================================================================
# ФАКТЫ О ПОЛЬЗОВАТЕЛЕ
# =============================================================================

def save_fact(user_id, key, value):
    """Сохраняет факт о пользователе"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT facts_json FROM user_facts WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    facts = json.loads(row[0]) if row else {}
    facts[key] = value
    cursor.execute("""
        INSERT OR REPLACE INTO user_facts (user_id, facts_json) 
        VALUES (?, ?)
    """, (user_id, json.dumps(facts, ensure_ascii=False)))
    conn.commit()
    conn.close()


def get_facts(user_id):
    """Получает все факты о пользователе"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT facts_json FROM user_facts WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else {}


def get_database_stats():
    """Возвращает статистику по базе данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
    stats['total_users'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM messages")
    stats['total_messages'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM summaries")
    stats['total_summaries'] = cursor.fetchone()[0]
    conn.close()
    return stats
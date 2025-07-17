#!/usr/bin/env python3
"""
Тест локальных эмбеддингов
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.vector_db import test_embedding_service, get_embedding


async def main():
    print("🧠 Тестирование локальных эмбеддингов...")
    print("=" * 50)
    
    # 1. Тест сервиса эмбеддингов
    print("\n1️⃣ Проверка сервиса эмбеддингов...")
    result = await test_embedding_service()
    
    if result['success']:
        print(f"✅ Сервис работает!")
        print(f"   Модель: {result['model']}")
        print(f"   Размер эмбеддинга: {result['embedding_size']}")
    else:
        print(f"❌ Ошибка: {result['error']}")
        return
    
    # 2. Тест с русским текстом
    print("\n2️⃣ Тест с русским текстом...")
    russian_text = "Привет! Как дела? Работаем над проектом."
    
    try:
        embedding = await get_embedding(russian_text)
        print(f"✅ Русский текст обработан успешно")
        print(f"   Размер эмбеддинга: {len(embedding)}")
        print(f"   Первые 5 значений: {embedding[:5]}")
    except Exception as e:
        print(f"❌ Ошибка с русским текстом: {e}")
    
    # 3. Тест с английским текстом
    print("\n3️⃣ Тест с английским текстом...")
    english_text = "Hello! How are you doing? Working on the project."
    
    try:
        embedding = await get_embedding(english_text)
        print(f"✅ Английский текст обработан успешно")
        print(f"   Размер эмбеддинга: {len(embedding)}")
        print(f"   Первые 5 значений: {embedding[:5]}")
    except Exception as e:
        print(f"❌ Ошибка с английским текстом: {e}")
    
    # 4. Тест с длинным текстом
    print("\n4️⃣ Тест с длинным текстом...")
    long_text = """
    Это очень длинный текст для тестирования эмбеддингов.
    Он содержит много предложений и разную информацию.
    Мы тестируем как модель справляется с обработкой больших текстов.
    Это важно для нашего чат-бота, который будет работать с сообщениями команды.
    """
    
    try:
        embedding = await get_embedding(long_text)
        print(f"✅ Длинный текст обработан успешно")
        print(f"   Размер эмбеддинга: {len(embedding)}")
        print(f"   Первые 5 значений: {embedding[:5]}")
    except Exception as e:
        print(f"❌ Ошибка с длинным текстом: {e}")
    
    print("\n✅ Тестирование завершено!")


if __name__ == "__main__":
    asyncio.run(main()) 
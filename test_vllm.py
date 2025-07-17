#!/usr/bin/env python3
"""
Простой скрипт для тестирования vLLM сервера
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.llm import check_vllm_health, test_vllm_simple, get_answer


async def main():
    print("🚀 Тестирование vLLM сервера...")
    print("=" * 50)
    
    # 1. Проверка health endpoint
    print("\n1️⃣ Проверка статуса сервера...")
    health_info = await check_vllm_health()
    print(f"   URL: {health_info['url']}")
    print(f"   Модель: {health_info['model']}")
    print(f"   Статус: {health_info['status']}")
    print(f"   Сообщение: {health_info['message']}")
    
    if health_info['status'] != 'healthy':
        print("❌ vLLM сервер недоступен!")
        return
    
    # 2. Простой тест
    print("\n2️⃣ Простой тест генерации...")
    simple_answer = await test_vllm_simple()
    print(f"   Ответ: {simple_answer}")
    
    # 3. Тест с контекстом
    print("\n3️⃣ Тест с контекстом...")
    context = """
    Пользователь Иван: Привет всем! Как дела с проектом?
    Пользователь Мария: Привет! Работаю над API, должна закончить к вечеру.
    Пользователь Алексей: Я занимаюсь фронтендом, почти готов.
    Пользователь Иван: Отлично! Тогда завтра можем делать интеграцию.
    """
    question = "Над чем работает команда?"
    
    answer = await get_answer(context, question)
    print(f"   Вопрос: {question}")
    print(f"   Ответ: {answer}")
    
    print("\n✅ Тестирование завершено!")


if __name__ == "__main__":
    asyncio.run(main()) 
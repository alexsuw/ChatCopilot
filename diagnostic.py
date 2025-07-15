#!/usr/bin/env python3
"""
Диагностический скрипт для проверки всех сервисов ChatCopilot
"""

import asyncio
import logging
import os
from typing import Dict, Any
from src.settings import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ServiceDiagnostic:
    """Класс для диагностики сервисов"""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
    
    async def check_env_variables(self) -> bool:
        """Проверяет переменные окружения"""
        print("🔍 Проверка переменных окружения...")
        
        required_vars = {
            'BOT_TOKEN': 'Telegram Bot Token',
            'GOOGLE_API_KEY': 'Google Gemini API Key',
            'OPENAI_API_KEY': 'OpenAI API Key',
            'PINECONE_API_KEY': 'Pinecone API Key',
            'PINECONE_HOST': 'Pinecone Host',
            'SUPABASE_URL': 'Supabase URL',
            'SUPABASE_ANON_KEY': 'Supabase Anon Key',
            'SUPABASE_SERVICE_KEY': 'Supabase Service Key'
        }
        
        missing_vars = []
        
        for var, description in required_vars.items():
            try:
                value = getattr(settings, var.lower())
                if hasattr(value, 'get_secret_value'):
                    value = value.get_secret_value()
                
                if not value or value == f"your_{var.lower()}":
                    missing_vars.append(f"{var} ({description})")
                    print(f"❌ {var}: НЕ УСТАНОВЛЕН")
                else:
                    print(f"✅ {var}: Установлен ({value[:10]}...)")
                    
            except AttributeError:
                missing_vars.append(f"{var} ({description})")
                print(f"❌ {var}: НЕ НАЙДЕН")
        
        if missing_vars:
            print(f"\n⚠️ Отсутствуют переменные окружения:")
            for var in missing_vars:
                print(f"  - {var}")
            return False
        
        print("✅ Все переменные окружения настроены")
        return True
    
    async def check_gemini(self) -> bool:
        """Проверяет работу Google Gemini"""
        print("\n🤖 Проверка Google Gemini...")
        
        try:
            from src.services.llm import get_answer
            
            test_context = "Тестовый контекст: обсуждение погоды"
            test_question = "Какая погода?"
            
            answer = await get_answer(test_context, test_question)
            
            if "❌" in answer:
                print(f"❌ Gemini вернул ошибку: {answer}")
                return False
            elif len(answer) < 10:
                print(f"⚠️ Слишком короткий ответ: {answer}")
                return False
            else:
                print(f"✅ Gemini работает корректно")
                print(f"   Ответ: {answer[:50]}...")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            return False
    
    async def check_openai(self) -> bool:
        """Проверяет работу OpenAI"""
        print("\n🧠 Проверка OpenAI...")
        
        try:
            from src.services.vector_db import get_embedding
            
            test_text = "Тестовый текст для создания эмбеддинга"
            
            embedding = await get_embedding(test_text)
            
            if embedding and len(embedding) > 0:
                print(f"✅ OpenAI работает корректно")
                print(f"   Размер эмбеддинга: {len(embedding)}")
                return True
            else:
                print("❌ OpenAI вернул пустой эмбеддинг")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка OpenAI: {e}")
            return False
    
    async def check_pinecone(self) -> bool:
        """Проверяет работу Pinecone"""
        print("\n📊 Проверка Pinecone...")
        
        try:
            from src.services.vector_db import pinecone_index, get_namespace_stats
            
            # Проверяем подключение к индексу
            stats = pinecone_index.describe_index_stats()
            print(f"✅ Pinecone подключен")
            print(f"   Общее количество векторов: {stats.total_vector_count}")
            print(f"   Размерность: {stats.dimension}")
            
            # Проверяем конкретный namespace
            test_namespace = "test-team-123"
            ns_stats = get_namespace_stats(test_namespace)
            print(f"   Векторов в тестовом namespace: {ns_stats.get('vector_count', 0)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка Pinecone: {e}")
            return False
    
    async def check_supabase(self) -> bool:
        """Проверяет работу Supabase"""
        print("\n🗄️ Проверка Supabase...")
        
        try:
            from src.services.supabase_client import supabase
            
            # Проверяем подключение
            response = supabase.table('teams').select('id').limit(1).execute()
            
            print(f"✅ Supabase подключен")
            print(f"   Количество записей в таблице teams: {len(response.data) if response.data else 0}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка Supabase: {e}")
            return False
    
    async def run_full_diagnostic(self):
        """Запускает полную диагностику"""
        print("🚀 Запуск полной диагностики ChatCopilot")
        print("=" * 60)
        
        # Проверки
        checks = [
            ("Переменные окружения", self.check_env_variables),
            ("Google Gemini", self.check_gemini),
            ("OpenAI", self.check_openai),
            ("Pinecone", self.check_pinecone),
            ("Supabase", self.check_supabase)
        ]
        
        passed = 0
        total = len(checks)
        
        for name, check_func in checks:
            try:
                result = await check_func()
                self.results[name] = result
                if result:
                    passed += 1
            except Exception as e:
                print(f"❌ Критическая ошибка при проверке {name}: {e}")
                self.results[name] = False
        
        # Итоговый отчет
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ")
        print("=" * 60)
        
        for name, result in self.results.items():
            status = "✅ РАБОТАЕТ" if result else "❌ НЕ РАБОТАЕТ"
            print(f"{name:.<30} {status}")
        
        print(f"\nПройдено проверок: {passed}/{total}")
        
        # Рекомендации
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        
        if not self.results.get("Переменные окружения", False):
            print("1. Создайте файл .env на основе env.example")
            print("2. Заполните все необходимые API ключи")
        
        if not self.results.get("Google Gemini", False):
            print("3. Проверьте правильность GOOGLE_API_KEY")
            print("4. Убедитесь, что у вас есть доступ к Gemini API")
            print("5. Проверьте квоты Google API")
        
        if not self.results.get("OpenAI", False):
            print("6. Проверьте правильность OPENAI_API_KEY")
            print("7. Убедитесь, что у вас есть баланс на OpenAI")
        
        if not self.results.get("Pinecone", False):
            print("8. Проверьте правильность PINECONE_API_KEY и PINECONE_HOST")
            print("9. Убедитесь, что индекс Pinecone создан")
        
        if not self.results.get("Supabase", False):
            print("10. Проверьте правильность настроек Supabase")
            print("11. Убедитесь, что таблицы созданы")
        
        if passed == total:
            print("\n🎉 ВСЕ СЕРВИСЫ РАБОТАЮТ КОРРЕКТНО!")
            print("Ваш бот готов к работе.")
        else:
            print(f"\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ ({total - passed} из {total})")
            print("Исправьте указанные проблемы перед запуском бота.")

if __name__ == "__main__":
    diagnostic = ServiceDiagnostic()
    asyncio.run(diagnostic.run_full_diagnostic()) 
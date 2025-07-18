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
            'VLLM_URL': 'vLLM Server URL',
            'VLLM_MODEL_NAME': 'vLLM Model Name',
            # 'PINECONE_API_KEY': 'Pinecone API Key',  # ОТКЛЮЧЕНО - НЕ ИСПОЛЬЗУЕМ ВЕКТОРНУЮ БД
            # 'PINECONE_HOST': 'Pinecone Host',        # ОТКЛЮЧЕНО - НЕ ИСПОЛЬЗУЕМ ВЕКТОРНУЮ БД
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
    
    async def check_vllm(self) -> bool:
        """Проверяет работу vLLM сервера"""
        print("\n🤖 Проверка vLLM...")
        
        try:
            from src.services.llm import check_vllm_health, test_vllm_simple
            
            # Проверяем health endpoint
            health_info = await check_vllm_health()
            print(f"   URL: {health_info['url']}")
            print(f"   Модель: {health_info['model']}")
            print(f"   Статус: {health_info['status']}")
            
            if health_info['status'] != 'healthy':
                print(f"❌ vLLM недоступен: {health_info['message']}")
                return False
            
            # Проверяем генерацию ответа
            print("   Тестирование генерации...")
            answer = await test_vllm_simple()
            
            if "❌" in answer:
                print(f"❌ vLLM вернул ошибку: {answer}")
                return False
            elif len(answer) < 10:
                print(f"⚠️ Слишком короткий ответ: {answer}")
                return False
            else:
                print(f"✅ vLLM работает корректно")
                print(f"   Ответ: {answer[:50]}...")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка vLLM: {e}")
            return False
    
    async def check_embeddings(self) -> bool:
        """Проверяет работу локальных эмбеддингов"""
        print("\n🧠 Проверка локальных эмбеддингов...")
        
        try:
            from src.services.vector_db import test_embedding_service
            
            result = await test_embedding_service()
            
            if result['success']:
                print(f"✅ Эмбеддинги работают корректно")
                print(f"   Модель: {result['model']}")
                print(f"   Размер эмбеддинга: {result['embedding_size']}")
                return True
            else:
                print(f"❌ Ошибка эмбеддингов: {result['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при проверке эмбеддингов: {e}")
            return False
    
    # async def check_pinecone(self) -> bool:  # ОТКЛЮЧЕНО - НЕ ИСПОЛЬЗУЕМ ВЕКТОРНУЮ БД
    #     """Проверяет работу Pinecone"""
    #     print("\n📊 Проверка Pinecone...")
    #     
    #     try:
    #         from src.services.vector_db import pinecone_index, get_namespace_stats
    #         
    #         # Проверяем подключение к индексу
    #         stats = pinecone_index.describe_index_stats()
    #         print(f"✅ Pinecone подключен")
    #         print(f"   Общее количество векторов: {stats.total_vector_count}")
    #         print(f"   Размерность: {stats.dimension}")
    #         
    #         # Проверяем конкретный namespace
    #         test_namespace = "test-team-123"
    #         ns_stats = get_namespace_stats(test_namespace)
    #         print(f"   Векторов в тестовом namespace: {ns_stats.get('vector_count', 0)}")
    #         
    #         return True
    #         
    #     except Exception as e:
    #         print(f"❌ Ошибка Pinecone: {e}")
    #         return False
    
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
            ("vLLM", self.check_vllm),
            # ("Эмбеддинги", self.check_embeddings),  # ОТКЛЮЧЕНО - НЕ ИСПОЛЬЗУЕМ ВЕКТОРНУЮ БД
            # ("Pinecone", self.check_pinecone),      # ОТКЛЮЧЕНО - НЕ ИСПОЛЬЗУЕМ ВЕКТОРНУЮ БД
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
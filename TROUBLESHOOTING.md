# 🔧 Руководство по устранению проблем

## Проблема: Gemini не отвечает

### Быстрая диагностика

1. **Запустите диагностический скрипт:**
   ```bash
   python diagnostic.py
   ```

2. **Проверьте только Gemini:**
   ```bash
   python test_gemini.py
   ```

### Возможные причины и решения

#### 1. ❌ Неправильный API ключ
**Симптомы:**
- Ошибка "Invalid Google API key"
- Код ошибки 401

**Решение:**
1. Проверьте правильность `GOOGLE_API_KEY` в `.env`
2. Убедитесь, что ключ активен в [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Проверьте, что ключ не заблокирован

#### 2. ❌ Превышение квот
**Симптомы:**
- Ошибка "Google API quota exceeded"
- Код ошибки 429

**Решение:**
1. Проверьте квоты в [Google Cloud Console](https://console.cloud.google.com/apis/api/generativeai.googleapis.com/quotas)
2. Увеличьте лимиты или подождите сброса квот
3. Рассмотрите возможность перехода на платный план

#### 3. ❌ Блокировка контента
**Симптомы:**
- Ошибка "Content blocked by safety filters"
- Пустые ответы от Gemini

**Решение:**
1. Проверьте содержимое сообщений на предмет нарушения политик
2. Измените настройки безопасности в `src/services/llm.py`
3. Переформулируйте системные сообщения

#### 4. ❌ Сетевые проблемы
**Симптомы:**
- Ошибки таймаута
- Сообщения о проблемах с сетью

**Решение:**
1. Проверьте подключение к интернету
2. Убедитесь, что нет блокировки Google API
3. Попробуйте использовать VPN

#### 5. ❌ Неправильный формат запроса
**Симптомы:**
- Пустые ответы
- Ошибки валидации

**Решение:**
1. Проверьте длину промпта (должна быть < 1M токенов)
2. Убедитесь, что контекст содержит текст
3. Проверьте кодировку сообщений

## Логи и отладка

### Включение детального логирования

Добавьте в начало `main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Проверка логов Gemini

Ищите в логах:
- `🤖 Gemini request attempt` - начало запроса
- `✅ Gemini response received` - успешный ответ
- `❌ Gemini error` - ошибки API
- `🚫 Content blocked` - блокировка контента

### Тестирование отдельных компонентов

```bash
# Только Gemini
python test_gemini.py

# Все сервисы
python diagnostic.py

# Запуск с отладкой
python -m pdb main.py
```

## Конфигурация Gemini

### Изменение настроек безопасности

В `src/services/llm.py` измените `safety_settings`:

```python
safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_ONLY_HIGH"  # Более мягкий фильтр
  },
  # ... остальные настройки
]
```

### Изменение параметров генерации

```python
generation_config = {
  "temperature": 0.5,        # Более консервативные ответы
  "top_p": 0.8,
  "top_k": 40,
  "max_output_tokens": 1024, # Более короткие ответы
}
```

## Мониторинг и профилактика

### Настройка мониторинга

1. Регулярно запускайте диагностику:
   ```bash
   # Добавьте в cron
   0 */6 * * * cd /path/to/bot && python diagnostic.py
   ```

2. Отслеживайте использование квот в Google Cloud Console

3. Настройте алерты для критических ошибок

### Предотвращение проблем

1. **Ротация API ключей** - меняйте ключи раз в месяц
2. **Кэширование ответов** - избегайте дублирующих запросов
3. **Обработка ошибок** - всегда предусматривайте fallback
4. **Мониторинг квот** - следите за использованием

## Часто задаваемые вопросы

**Q: Почему Gemini работает в тестах, но не в боте?**
A: Проверьте различия в окружении и логах. Возможно, проблема в параллельных запросах.

**Q: Можно ли использовать другую модель вместо Gemini?**
A: Да, можно адаптировать код для работы с OpenAI GPT или другими моделями.

**Q: Как увеличить скорость ответов?**
A: Уменьшите `max_output_tokens` и `temperature` в конфигурации.

**Q: Что делать, если проблема не решается?**
A: Создайте issue в репозитории с логами и результатами диагностики.

## Контакты для поддержки

- **Telegram**: @your_support_bot
- **Email**: support@example.com
- **GitHub Issues**: [Ссылка на репозиторий]

---

> 💡 **Совет**: Сохраните результаты диагностики перед обращением в поддержку:
> ```bash
> python diagnostic.py > diagnostic_results.txt 2>&1
> ``` 
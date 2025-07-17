# Настройка локальных эмбеддингов для ChatCopilot

## Что изменилось

Проект переведен с **OpenAI Embeddings** на **локальные эмбеддинги** для обхода географических ограничений.

### Удаленные компоненты:
- `openai` зависимость для эмбеддингов
- `OPENAI_API_KEY` переменная окружения
- Зависимость от OpenAI API для создания векторов

### Добавленные компоненты:
- `sentence-transformers` для локальных эмбеддингов
- Многоязычная модель поддерживающая русский язык
- Асинхронная обработка эмбеддингов
- Улучшенная обработка ошибок

## Используемая модель

**Модель**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

### Особенности:
- 🌍 Поддержка 50+ языков включая русский
- 📏 Размер эмбеддинга: 384 измерения
- 🚀 Быстрая обработка локально
- 💾 Работает без интернета после загрузки

## Установка зависимостей

```bash
pip install -r requirements.txt
```

Новые зависимости:
- `sentence-transformers==2.2.2`
- `torch==2.0.1`

## Первый запуск

При первом запуске модель автоматически загрузится:

```bash
python test_embeddings.py
```

### Размер загрузки:
- Модель: ~120 MB
- Загружается автоматически при первом использовании
- Сохраняется в `~/.cache/torch/sentence_transformers/`

## Тестирование

### 1. Тест эмбеддингов:
```bash
python test_embeddings.py
```

### 2. Полная диагностика:
```bash
python diagnostic.py
```

### 3. Тест в коде:
```python
from src.services.vector_db import get_embedding

# Тест
embedding = await get_embedding("Привет, как дела?")
print(f"Размер эмбеддинга: {len(embedding)}")
```

## Обновленные переменные окружения

Убрана из `.env`:
```bash
# OPENAI_API_KEY - больше не нужна
```

Осталось без изменений:
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_HOST=your_pinecone_index_host
```

## Производительность

### Скорость обработки:
- Короткий текст (10-50 слов): ~0.1-0.2 сек
- Средний текст (100-200 слов): ~0.2-0.5 сек
- Длинный текст (500+ слов): ~0.5-1.0 сек

### Совместимость:
- **CPU**: Работает на любом процессоре
- **GPU**: Автоматически использует CUDA если доступно
- **RAM**: Требует ~500MB для загруженной модели

## Устранение неполадок

### 1. Модель не загружается
```
❌ Failed to load embedding model
```
**Решение:**
```bash
pip install sentence-transformers torch
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

### 2. Медленная обработка
```
⚠️ Embedding takes too long
```
**Решение:**
- Проверьте доступность GPU: `torch.cuda.is_available()`
- Обновите PyTorch: `pip install torch --upgrade`
- Используйте более мощное железо

### 3. Ошибки памяти
```
❌ CUDA out of memory
```
**Решение:**
- Модель переключится на CPU автоматически
- Закройте другие процессы
- Уменьшите размер батча

## Сравнение с OpenAI

| Параметр | OpenAI | Локальные эмбеддинги |
|----------|---------|---------------------|
| Интернет | Требуется | Не требуется |
| Стоимость | Платный | Бесплатный |
| Скорость | 0.5-2 сек | 0.1-1 сек |
| Размер | 1536 | 384 |
| Языки | 100+ | 50+ |
| Приватность | Нет | Да |

## Совместимость с Pinecone

✅ Векторы полностью совместимы с Pinecone
✅ Namespace изоляция работает
✅ Поиск по векторам работает
✅ Метаданные сохраняются

## Мониторинг

Логи эмбеддингов:
```bash
tail -f logs/app.log | grep "embedding"
```

Проверка статуса:
```bash
python -c "
import asyncio
from src.services.vector_db import test_embedding_service
result = asyncio.run(test_embedding_service())
print(f'Status: {result}')
"
```

## Обновление модели

Для смены модели отредактируйте `src/services/vector_db.py`:

```python
# Другие модели:
# 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'  # Лучше качество, больше размер
# 'sentence-transformers/distiluse-base-multilingual-cased'      # Быстрее, меньше качество
```

Перезапустите сервис после изменения модели. 
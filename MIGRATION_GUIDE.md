# Руководство по миграции с Appwrite на Supabase

## 🎯 Обзор миграции

Проект ChatCopilot был успешно мигрирован с **Appwrite** на **Supabase** для использования PostgreSQL вместо NoSQL, что обеспечивает:

- ✅ Лучшую производительность для сложных запросов
- ✅ ACID совместимость транзакций  
- ✅ Встроенную поддержку внешних ключей
- ✅ Более мощные инструменты для анализа данных
- ✅ Лучшую интеграцию с современными инструментами разработки

## 📊 Сравнение архитектур

### Appwrite (старая версия)
```
🗄️ Appwrite NoSQL → 4 коллекции
├── teams (документы)
├── users (документы)  
├── user_teams (документы)
└── linked_chats (документы)
```

### Supabase (новая версия)
```
🐘 PostgreSQL → 4 таблицы
├── teams (релационная таблица)
├── users (релационная таблица)
├── user_teams (junction table с FK)
└── linked_chats (релационная таблица с FK)
```

## 🔄 Изменения в коде

### 1. Новый клиент базы данных

**Старо:** `src/services/appwrite_client.py`
```python
from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
databases = Databases(client)
```

**Новое:** `src/services/supabase_client.py`
```python
from supabase import create_client, Client

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key
)
```

### 2. Изменения в API

| Операция | Appwrite | Supabase |
|----------|----------|----------|
| Создание записи | `databases.create_document()` | `supabase.table().insert()` |
| Получение записи | `databases.get_document()` | `supabase.table().select().eq()` |
| Обновление записи | `databases.update_document()` | `supabase.table().update().eq()` |
| Поиск записей | `databases.list_documents()` | `supabase.table().select().eq()` |

### 3. Изменения в типах данных

| Поле | Appwrite | Supabase |
|------|----------|----------|
| ID команды | `String` | `UUID` |
| ID пользователя | `String` | `BIGINT` |
| ID чата | `String` | `BIGINT` |
| Временные метки | отсутствуют | `TIMESTAMPTZ` |

## 🛠️ Настройка нового проекта

### 1. Supabase проект (уже создан)

- **Project ID:** `rpvqvjebqwfakztfrhtt`
- **URL:** `https://rpvqvjebqwfakztfrhtt.supabase.co`
- **Region:** `us-east-1`

### 2. Новые переменные окружения

Обновите ваш `.env` файл:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# AI Services
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_HOST=your_pinecone_index_host
GOOGLE_API_KEY=your_google_api_key

# Supabase (заменяет Appwrite)
SUPABASE_URL=https://rpvqvjebqwfakztfrhtt.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJwdnF2amVicXdmYWt6dGZyaHR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIwNDUwNjAsImV4cCI6MjA2NzYyMTA2MH0.NS5t-sUnXdHTLrnZBfLeM-rZxU2uyeh_BsNOHkj6IKg
SUPABASE_SERVICE_KEY=your_supabase_service_key_here
```

### 3. Обновленные зависимости

В `requirements.txt`:

```diff
- appwrite==4.0.0
+ supabase==2.4.1
```

## 🗄️ Схема базы данных

Новая PostgreSQL схема уже создана и включает:

### Таблица `teams`
```sql
CREATE TABLE teams (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    invite_code VARCHAR(50) UNIQUE NOT NULL,
    admin_id BIGINT NOT NULL,
    system_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Таблица `users`
```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Таблица `user_teams` (Many-to-Many)
```sql
CREATE TABLE user_teams (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id BIGINT NOT NULL,
    team_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'member')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    UNIQUE(user_id, team_id)
);
```

### Таблица `linked_chats`
```sql
CREATE TABLE linked_chats (
    id BIGINT PRIMARY KEY,
    team_id UUID NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);
```

## 🔐 Безопасность и RLS

- ✅ Row Level Security (RLS) включен для всех таблиц
- ✅ Политики безопасности настроены
- ✅ Индексы созданы для оптимизации производительности
- ✅ Автоматические триггеры для обновления `updated_at`

## 🚀 Развертывание

### 1. Локальная разработка

```bash
# Установите новые зависимости
pip install -r requirements.txt

# Обновите переменные окружения
cp env.example .env
# Отредактируйте .env со своими API ключами

# Запустите бота
python main.py
```

### 2. Docker развертывание

```bash
# Пересоберите образ
docker build -t chatcopilot .

# Запустите контейнер
docker run -d --name chatcopilot --env-file .env chatcopilot
```

## 📈 Преимущества миграции

### Производительность
- 🚀 Более быстрые сложные запросы с JOIN
- 🚀 Лучшая индексация PostgreSQL
- 🚀 Автоматическая оптимизация запросов

### Надежность
- 🔒 ACID транзакции для консистентности данных
- 🔒 Референциальная целостность с внешними ключами
- 🔒 Встроенное резервное копирование

### Разработка
- 🛠️ Лучшие инструменты для SQL
- 🛠️ Встроенная панель администрирования Supabase
- 🛠️ Автоматическая генерация TypeScript типов

## 🆘 Устранение неполадок

### Частые проблемы

1. **Ошибки подключения к Supabase**
   ```
   Проверьте SUPABASE_URL и SUPABASE_ANON_KEY в .env
   ```

2. **Ошибки прав доступа**
   ```
   Убедитесь что RLS политики настроены правильно
   ```

3. **Проблемы с типами данных**
   ```
   Telegram ID должны быть BIGINT, а не String
   ```

## 🔄 Откат (если необходимо)

Если нужно вернуться к Appwrite:

1. Восстановите `appwrite_client.py` из git истории
2. Обновите импорты в обработчиках
3. Верните старые переменные окружения
4. Откатите `requirements.txt`

## ✅ Проверочный список миграции

- [x] Supabase проект создан
- [x] PostgreSQL схема развернута  
- [x] Код обновлен для Supabase
- [x] Зависимости обновлены
- [x] Переменные окружения настроены
- [x] Документация обновлена
- [x] Старые файлы удалены

## 🎉 Результат

**ChatCopilot** теперь работает на современном, масштабируемом и надежном PostgreSQL стеке!

Все функции остаются точно такими же для пользователей, но теперь система работает значительно быстрее и надежнее. 
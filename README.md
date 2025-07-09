# ChatCopilot 🤖
## Умный ассистент для командной работы

ChatCopilot — это Telegram-бот, который превращает хаос в чатах в организованную базу знаний. Бот автоматически собирает и анализирует сообщения из групповых чатов команды, а затем использует эти данные для ответов на вопросы участников с помощью технологии RAG (Retrieval-Augmented Generation).

## 🏗️ Архитектура проекта

### Общая структура
```
ChatCopilot/
├── main.py                    # Точка входа приложения
├── requirements.txt           # Зависимости Python
├── Dockerfile                # Конфигурация Docker
├── .gcloudignore             # Игнорируемые файлы для Google Cloud
└── src/                      # Исходный код
    ├── settings.py           # Настройки и переменные окружения
    ├── handlers/             # Обработчики команд и сообщений
    │   ├── basic.py          # Базовые команды (/start, /help)
    │   ├── team_management.py # Управление командами
    │   ├── message_ingestion.py # Сбор и обработка сообщений
    │   └── qa_session.py     # Сессии вопросов-ответов
    ├── services/             # Сервисы для работы с внешними API
    │   ├── supabase_client.py # Клиент для работы с Supabase DB
    │   ├── llm.py            # Сервис работы с LLM (Google Gemini)
    │   └── vector_db.py      # Сервис работы с векторной БД (Pinecone)
    ├── states/               # FSM состояния для aiogram
    │   └── team.py           # Состояния для управления командами
    └── keyboards/            # Inline клавиатуры
        └── inline.py         # Клавиатуры для выбора команд
```

### Технологический стек

#### Backend Framework
- **aiogram 3.4.1** - Асинхронный фреймворк для Telegram Bot API
- **Python 3.11** - Основной язык программирования

#### Базы данных
- **Supabase 2.4.1** - PostgreSQL база данных (основная БД)
- **Pinecone** - Векторная база данных для хранения эмбеддингов

#### AI/ML Сервисы
- **Google Gemini 1.5-flash** - Основной LLM для генерации ответов
- **OpenAI text-embedding-3-small** - Модель для создания эмбеддингов
- **Pinecone** - Векторный поиск для RAG

#### Другие зависимости
- **pydantic-settings** - Управление настройками
- **httpx** - HTTP клиент
- **numpy** - Математические операции

### Архитектура данных

#### База данных Supabase (PostgreSQL)
Проект использует 4 таблицы:

1. **teams** - Команды
   ```sql
   CREATE TABLE teams (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     name VARCHAR(255) NOT NULL,
     invite_code VARCHAR(50) UNIQUE NOT NULL,
     admin_id BIGINT NOT NULL,
     system_message TEXT,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

2. **users** - Пользователи
   ```sql
   CREATE TABLE users (
     id BIGINT PRIMARY KEY,
     username VARCHAR(255),
     first_name VARCHAR(255),
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

3. **user_teams** - Связи пользователь-команда (many-to-many)
   ```sql
   CREATE TABLE user_teams (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     user_id BIGINT REFERENCES users(id),
     team_id UUID REFERENCES teams(id),
     role VARCHAR(20) CHECK (role IN ('admin', 'member')),
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

4. **linked_chats** - Привязанные чаты
   ```sql
   CREATE TABLE linked_chats (
     id BIGINT PRIMARY KEY,
     team_id UUID REFERENCES teams(id),
     title VARCHAR(255),
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

#### Векторная база данных (Pinecone)
- **Namespace**: `team-{team_id}` - изоляция данных по командам
- **Vectors**: Эмбеддинги сообщений с метаданными
- **Metadata**: Текст оригинального сообщения

## 🔧 Основная функциональность

### 1. Управление командами
- **Создание команды** (`/create_team`)
- **Присоединение к команде** (`/join_team`)
- **Просмотр команд** (`/my_teams`)
- **Настройка системного сообщения** (`/set_system_message`)

### 2. Привязка чатов
- **Привязка группового чата** (`/link_chat`)
- Только администраторы команд могут привязывать чаты

### 3. Сбор и обработка сообщений
- **Автоматический сбор** сообщений из привязанных групповых чатов
- **Батчевая обработка** (CHUNK_SIZE = 5 сообщений)
- **Создание эмбеддингов** через OpenAI
- **Сохранение в Pinecone** с namespace изоляцией

### 4. Q&A сессии
- **Интерактивные сессии** вопросов-ответов
- **RAG Pipeline**: поиск релевантного контекста + генерация ответа
- **Кастомные системные сообщения** для каждой команды

## 🔄 Поток данных (Data Flow)

### 1. Сбор сообщений
```
Групповой чат → message_ingestion.py → Буфер (5 сообщений) → 
OpenAI Embeddings → Pinecone (team namespace)
```

### 2. Обработка вопросов
```
Пользователь задает вопрос → OpenAI Embeddings → 
Pinecone поиск (top-k=3) → Построение контекста → 
Google Gemini → Ответ пользователю
```

## 🚀 Развертывание

### Переменные окружения
Создайте файл `.env` со следующими переменными:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# AI Services
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_HOST=your_pinecone_index_host
GOOGLE_API_KEY=your_google_api_key

# Supabase
SUPABASE_URL=https://rpvqvjebqwfakztfrhtt.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJwdnF2amVicXdmYWt6dGZyaHR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIwNDUwNjAsImV4cCI6MjA2NzYyMTA2MH0.NS5t-sUnXdHTLrnZBfLeM-rZxU2uyeh_BsNOHkj6IKg
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### Локальный запуск
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python main.py
```

### Docker
```bash
# Сборка образа
docker build -t chatcopilot .

# Запуск контейнера
docker run -d --name chatcopilot --env-file .env chatcopilot
```

### Google Cloud Run
```bash
# Развертывание на Google Cloud
gcloud run deploy chatcopilot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 📋 Команды бота

| Команда | Описание | Доступ |
|---------|----------|--------|
| `/start` | Перезапуск бота и приветствие | Все |
| `/help` | Справка по командам | Все |
| `/create_team` | Создание новой команды | Все |
| `/join_team` | Присоединение к команде по коду | Все |
| `/my_teams` | Просмотр своих команд и начало диалога | Все |
| `/link_chat` | Привязка группового чата к команде | Админы команд |
| `/set_system_message` | Настройка системного сообщения | Админы команд |

## 🔒 Безопасность и изоляция

- **Namespace изоляция** в Pinecone по командам
- **Роли пользователей** (admin/member) с разными правами
- **Проверка прав** на привязку чатов и настройку системных сообщений
- **Безопасная обработка** API ключей через SecretStr

## 📊 Мониторинг и логирование

- **Структурированное логирование** всех операций
- **Обработка ошибок** Appwrite и внешних сервисов
- **Graceful degradation** при недоступности сервисов

## 🐛 Известные проблемы

1. **Keyboard bug**: В `keyboards/inline.py` используется неправильный ключ `'id'` вместо `'$id'`
2. **Requirements inconsistency**: Расхождения в версиях appwrite между файлами requirements.txt
3. **Missing .env.example**: Нет примера файла с переменными окружения

## 🚧 Планы развития

- [ ] Добавление поддержки файлов и медиа
- [ ] Улучшение качества RAG (re-ranking, hybrid search)
- [ ] Web интерфейс для управления командами
- [ ] Аналитика использования
- [ ] Многоязычная поддержка

## 🤝 Вклад в проект

Проект открыт для вклада! Пожалуйста, создавайте Issues и Pull Requests для улучшения функциональности.

---

*ChatCopilot - превращаем командные чаты в умную базу знаний* 🚀 
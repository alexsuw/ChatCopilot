# 🚀 Руководство по деплою ChatCopilot на Digital Ocean

## Предварительные требования

1. **Аккаунт Digital Ocean** - [Зарегистрироваться](https://www.digitalocean.com/)
2. **Telegram Bot Token** - создайте бота через [@BotFather](https://t.me/botfather)
3. **Supabase проект** - [Создать на supabase.com](https://supabase.com/)
4. **Google AI API Key** - [Получить на ai.google.dev](https://ai.google.dev/)
5. **Pinecone API Key** - [Создать аккаунт на pinecone.io](https://www.pinecone.io/)

## Настройка переменных окружения

Скопируйте файл `env.example` и заполните все переменные:

```bash
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Google AI
GOOGLE_AI_API_KEY=your_google_ai_api_key

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment

# OpenAI (опционально)
OPENAI_API_KEY=your_openai_api_key

# Настройки приложения
ENVIRONMENT=production
DEBUG=false
```

## Деплой на Digital Ocean App Platform

### Метод 1: Через веб-интерфейс (рекомендуется)

1. **Войдите в Digital Ocean Console**
   - Перейдите на [cloud.digitalocean.com](https://cloud.digitalocean.com/)
   - Войдите в свой аккаунт

2. **Создайте новое приложение**
   - Нажмите "Create" → "Apps"
   - Выберите "GitHub" как источник
   - Подключите свой GitHub аккаунт
   - Выберите репозиторий `ChatCopilot`
   - Выберите ветку `main`

3. **Настройте тип приложения**
   - **Тип**: Worker (не Web Service!)
   - **Name**: chatcopilot-worker
   - **Source Directory**: оставьте пустым (корень репозитория)
   - **Dockerfile Path**: Dockerfile

4. **Настройте план**
   - Выберите **Basic Plan**
   - **Container Size**: $5/month (512 MB RAM, 1 vCPU) - достаточно для начала
   - При необходимости можно масштабировать

5. **Добавьте переменные окружения**
   - Перейдите в раздел "Environment Variables"
   - Добавьте все переменные из файла `.env`:
     ```
     BOT_TOKEN: your_telegram_bot_token_here
     SUPABASE_URL: your_supabase_project_url
     SUPABASE_KEY: your_supabase_anon_key
     GOOGLE_AI_API_KEY: your_google_ai_api_key
     PINECONE_API_KEY: your_pinecone_api_key
     PINECONE_ENVIRONMENT: your_pinecone_environment
     OPENAI_API_KEY: your_openai_api_key (опционально)
     ENVIRONMENT: production
     DEBUG: false
     ```
   - **Важно**: Отметьте чувствительные переменные как "Encrypted"

6. **Настройте Health Check**
   - **Отключите** HTTP Health Check (так как это worker, а не web service)

7. **Деплой**
   - Нажмите "Create Resources"
   - Дождитесь завершения сборки и деплоя (обычно 5-10 минут)

### Метод 2: Через Digital Ocean CLI

1. **Установите doctl CLI**
   ```bash
   # macOS
   brew install doctl
   
   # Linux
   wget https://github.com/digitalocean/doctl/releases/download/v1.92.0/doctl-1.92.0-linux-amd64.tar.gz
   tar xf doctl-1.92.0-linux-amd64.tar.gz
   sudo mv doctl /usr/local/bin
   ```

2. **Авторизуйтесь**
   ```bash
   doctl auth init
   ```

3. **Создайте app spec файл**
   Создайте файл `app.yaml`:
   ```yaml
   name: chatcopilot-worker
   services:
   - name: worker
     source_dir: /
     github:
       repo: alexsuw/ChatCopilot
       branch: main
     run_command: python main.py
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     dockerfile_path: Dockerfile
     envs:
     - key: BOT_TOKEN
       value: YOUR_BOT_TOKEN
       type: SECRET
     - key: SUPABASE_URL
       value: YOUR_SUPABASE_URL
     - key: SUPABASE_KEY
       value: YOUR_SUPABASE_KEY
       type: SECRET
     - key: GOOGLE_AI_API_KEY
       value: YOUR_GOOGLE_AI_API_KEY
       type: SECRET
     - key: PINECONE_API_KEY
       value: YOUR_PINECONE_API_KEY
       type: SECRET
     - key: PINECONE_ENVIRONMENT
       value: YOUR_PINECONE_ENVIRONMENT
     - key: ENVIRONMENT
       value: production
     - key: DEBUG
       value: "false"
   ```

4. **Деплой через CLI**
   ```bash
   doctl apps create --spec app.yaml
   ```

## Мониторинг и логи

### Просмотр логов
```bash
# Получите ID приложения
doctl apps list

# Просмотр логов
doctl apps logs APP_ID --follow
```

### В веб-интерфейсе
- Перейдите в Apps → Ваше приложение → Runtime Logs
- Здесь вы увидите все логи работы бота

## Управление приложением

### Рестарт
```bash
doctl apps create-deployment APP_ID
```

### Масштабирование
- Перейдите в Apps → Settings → Edit Plan
- Выберите более мощный план при необходимости

### Обновление кода
- Просто пушьте изменения в ветку `main`
- Digital Ocean автоматически пересоберет и задеплоит

## Troubleshooting

### Проблема: Бот не отвечает
1. Проверьте логи в Digital Ocean Console
2. Убедитесь, что все переменные окружения заданы правильно
3. Проверьте, что BOT_TOKEN корректный

### Проблема: Ошибки подключения к базе данных
1. Проверьте SUPABASE_URL и SUPABASE_KEY
2. Убедитесь, что в Supabase настроены нужные таблицы
3. Проверьте, что Supabase проект активен

### Проблема: Превышение лимитов
1. Проверьте использование ресурсов в Digital Ocean Console
2. При необходимости обновите план
3. Оптимизируйте код для снижения потребления памяти

## Стоимость

### Примерная стоимость при Basic плане:
- **Worker instance**: $5/месяц (512 MB RAM, 1 vCPU)
- **Bandwidth**: обычно входит в план
- **Build minutes**: 400 минут/месяц бесплатно

### Для большей нагрузки:
- **Professional plan**: от $12/месяц (1 GB RAM, 1 vCPU)
- **Автомасштабирование**: доступно в Professional плане

## Безопасность

1. **Используйте encrypted переменные** для API ключей
2. **Регулярно ротируйте** API ключи
3. **Мониторьте логи** на предмет подозрительной активности
4. **Используйте HTTPS** для всех внешних API

---

## 🎉 Готово!

После успешного деплоя ваш Telegram бот будет работать 24/7 на Digital Ocean. 

**Проверьте работу:** отправьте `/start` вашему боту в Telegram.

**Мониторинг:** следите за логами и метриками в Digital Ocean Console. 
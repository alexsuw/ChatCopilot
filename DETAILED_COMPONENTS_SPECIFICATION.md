# Детальная спецификация компонентов 

> [!WARNING]
> **Этот документ устарел.**
> 
> Изначально предложенная гибридная RAG-архитектура была признана избыточно сложной и дорогой для текущих задач проекта.
>
> **Актуальная и упрощенная архитектура описана в документе: [`SIMPLE_VERSION.md`](./SIMPLE_VERSION.md)**
>
> Пожалуйста, используйте его как единственно верный источник информации о технических компонентах проекта.

---

### Архивное описание (не используется)

Архивное содержимое этого документа сохранено для истории, но **не должно использоваться** для разработки или принятия решений.

<details>
<summary>Нажмите, чтобы увидеть устаревшую спецификацию</summary>

## Компонент 1: Иерархическая система контекста

### 🎯 **Назначение**
Многоуровневая система хранения и доступа к информации с приоритизацией по актуальности и важности.

### 🏗️ **Архитектурные уровни**

#### **Уровень 1: Живой контекст (Live Context)**

**Техническая реализация:**
```python
# Redis структура данных
{
    "live_context:team_123:2024-01-15:14": {
        "messages": [
            {
                "id": "msg_001",
                "content": "Обсуждаем новую архитектуру базы данных",
                "author": "alex",
                "timestamp": "2024-01-15T14:30:00Z",
                "importance": 0.85,
                "entities": ["база данных", "архитектура"],
                "thread_id": "thread_001"
            }
        ],
        "summary": "Обсуждение архитектуры БД",
        "participants": ["alex", "maria", "ivan"],
        "active_topics": ["database", "architecture"]
    }
}
```

**Self-hosted вариант:**
- **Redis Cluster**: 3 ноды по 16GB RAM
- **Настройка TTL**: 3 часа для live данных
- **Persistence**: RDB snapshots каждые 15 минут
- **Стоимость**: ~$450/месяц
- **Плюсы**: Полный контроль, низкая латентность
- **Минусы**: Необходимость администрирования

**API вариант:**
- **Redis Cloud**: Managed service
- **Автомасштабирование**: до 100GB по требованию
- **Стоимость**: ~$600/месяц
- **Плюсы**: Нет администрирования, SLA 99.9%
- **Минусы**: Выше стоимость, зависимость от провайдера

#### **Уровень 2: Дневные сводки (Daily Summaries)**

**Техническая реализация:**
```python
# PostgreSQL таблица с индексами
CREATE TABLE daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL,
    date DATE NOT NULL,
    summary TEXT NOT NULL,
    key_decisions TEXT[],
    active_participants TEXT[],
    main_topics TEXT[],
    sentiment_score FLOAT DEFAULT 0.0,
    activity_level INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_team_date UNIQUE(team_id, date)
);

-- Индексы для быстрого поиска
CREATE INDEX idx_daily_summaries_team_date ON daily_summaries(team_id, date DESC);
CREATE INDEX idx_daily_summaries_topics ON daily_summaries USING GIN(main_topics);
```

**Генерация сводок:**
```python
class DailySummaryGenerator:
    def __init__(self, summarization_model):
        self.model = summarization_model
        
    async def generate_daily_summary(self, team_id: str, date: datetime.date):
        # Получаем все сообщения дня
        messages = await self.get_day_messages(team_id, date)
        
        # Группируем по темам
        topic_groups = self.group_by_topics(messages)
        
        # Создаем резюме для каждой темы
        topic_summaries = []
        for topic, msgs in topic_groups.items():
            summary = await self.model.summarize(msgs, max_length=200)
            topic_summaries.append({
                'topic': topic,
                'summary': summary,
                'message_count': len(msgs)
            })
        
        # Создаем общее резюме дня
        daily_summary = await self.create_daily_overview(topic_summaries)
        
        return daily_summary
```

**Без обучения (готовые модели):**
- **T5-small**: Хорошо для русского языка
- **mT5-base**: Многоязычный вариант
- **BART**: Для английского языка
- **Качество**: 75-80% без fine-tuning

**С обучением (fine-tuned):**
- **Датасет**: 10K примеров сводок команд
- **Время обучения**: 2-3 дня на V100
- **Стоимость обучения**: ~$500
- **Качество**: 85-90% после fine-tuning

#### **Уровень 3: Тематические индексы (Topic Indexes)**

**Техническая реализация:**
```python
# Система автоматического определения тем
class TopicDetector:
    def __init__(self):
        self.clustering_model = None
        self.topic_embeddings = {}
        
    def detect_topics(self, messages: List[str]) -> Dict[str, List[str]]:
        # Получаем эмбеддинги сообщений
        embeddings = self.get_embeddings(messages)
        
        # Кластеризация по темам
        clusters = self.cluster_messages(embeddings)
        
        # Присваиваем темы кластерам
        topics = {}
        for cluster_id, message_ids in clusters.items():
            topic_name = self.generate_topic_name(message_ids)
            topics[topic_name] = message_ids
            
        return topics
```

**Self-hosted решение:**
- **Sentence-BERT**: Для создания эмбеддингов
- **HDBSCAN**: Для кластеризации
- **KeyBERT**: Для извлечения ключевых слов
- **Стоимость**: ~$200/месяц (GPU сервер)

**API решение:**
- **OpenAI Embeddings**: text-embedding-3-small
- **Pinecone**: Для векторного поиска
- **Стоимость**: ~$300/месяц
- **Плюсы**: Высокое качество, простота
- **Минусы**: Зависимость от API

#### **Уровень 4: Глубокий архив (Deep Archive)**

**Техническая реализация:**
```python
# Архивная система с компрессией
class DeepArchiveManager:
    def __init__(self):
        self.compression_enabled = True
        self.archive_threshold_days = 30
        
    async def archive_old_data(self, team_id: str):
        # Находим данные старше порога
        old_data = await self.find_old_data(team_id)
        
        # Компрессия и архивирование
        for data_batch in old_data:
            compressed = self.compress_data(data_batch)
            await self.store_in_archive(team_id, compressed)
            
    def compress_data(self, data: List[Dict]) -> bytes:
        # Удаляем избыточную информацию
        essential_data = self.extract_essential_info(data)
        
        # Сжимаем с помощью gzip
        return gzip.compress(json.dumps(essential_data).encode())
```

---

## Компонент 2: Предварительная обработка данных

### 🎯 **Назначение** 
Интеллектуальная обработка входящих сообщений с анализом важности, извлечением сущностей и структурированием данных.

### 🤖 **ML компоненты**

#### **2.1 Классификатор важности сообщений**

**Техническая реализация:**
```python
class MessageImportanceClassifier:
    def __init__(self, model_path: str = None):
        if model_path:
            self.model = self.load_model(model_path)
        else:
            self.model = self.load_pretrained_model()
    
    def classify_importance(self, message: str) -> float:
        # Извлекаем признаки
        features = self.extract_features(message)
        
        # Предсказываем важность (0.0 - 1.0)
        importance_score = self.model.predict(features)[0]
        
        return importance_score
    
    def extract_features(self, message: str) -> np.ndarray:
        return np.array([
            self.has_decision_keywords(message),
            self.has_question_marks(message),
            self.message_length(message),
            self.has_mentions(message),
            self.has_urls(message),
            self.sentiment_score(message),
            self.urgency_indicators(message)
        ])
```

**Без обучения (правила + простые модели):**
```python
class RuleBasedImportanceClassifier:
    def __init__(self):
        self.decision_keywords = ['решили', 'принимаем', 'утверждаем', 'делаем']
        self.question_keywords = ['как', 'что', 'когда', 'почему']
        self.urgent_keywords = ['срочно', 'немедленно', 'asap', 'критично']
    
    def classify_importance(self, message: str) -> float:
        score = 0.5  # базовый уровень
        
        # Проверяем наличие ключевых слов
        if any(kw in message.lower() for kw in self.decision_keywords):
            score += 0.3
        
        if any(kw in message.lower() for kw in self.urgent_keywords):
            score += 0.2
            
        # Длина сообщения
        if len(message) > 100:
            score += 0.1
            
        return min(score, 1.0)
```

**С обучением (fine-tuned модель):**
- **Базовая модель**: RuBERT или DistilBERT
- **Датасет**: 5K размеченных сообщений по важности
- **Разметка**: 0 (неважно) - 1 (критично)
- **Время обучения**: 4-6 часов на V100
- **Стоимость**: ~$100
- **Качество**: 85-90% accuracy

#### **2.2 Экстрактор сущностей (Named Entity Recognition)**

**Self-hosted вариант:**
```python
import spacy
from transformers import AutoTokenizer, AutoModelForTokenClassification

class EntityExtractor:
    def __init__(self):
        # Загружаем модель spaCy для русского языка
        self.nlp = spacy.load("ru_core_news_sm")
        
        # Дополнительная модель для специфичных сущностей
        self.custom_model = AutoModelForTokenClassification.from_pretrained(
            "DeepPavlov/rubert-base-cased-conversational"
        )
        
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        # Базовое извлечение сущностей
        doc = self.nlp(text)
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'projects': [],
            'technologies': []
        }
        
        # Стандартные сущности
        for ent in doc.ents:
            if ent.label_ == "PER":
                entities['persons'].append(ent.text)
            elif ent.label_ == "ORG":
                entities['organizations'].append(ent.text)
            elif ent.label_ == "LOC":
                entities['locations'].append(ent.text)
            elif ent.label_ == "DATE":
                entities['dates'].append(ent.text)
        
        # Кастомные сущности (проекты, технологии)
        custom_entities = self.extract_custom_entities(text)
        entities.update(custom_entities)
        
        return entities
```

**API вариант:**
```python
class APIEntityExtractor:
    def __init__(self):
        self.openai_client = OpenAI()
        
    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        prompt = f"""
        Извлеки из текста следующие сущности:
        - Люди (имена, упоминания)
        - Проекты 
        - Технологии
        - Даты и дедлайны
        - Решения
        
        Текст: {text}
        
        Верни в формате JSON.
        """
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        return json.loads(response.choices[0].message.content)
```

**Сравнение подходов:**
| Критерий | Self-hosted | API |
|----------|-------------|-----|
| Качество | 80-85% | 90-95% |
| Стоимость | $150/месяц | $400/месяц |
| Латентность | 50-100ms | 200-500ms |
| Кастомизация | Высокая | Низкая |

#### **2.3 Классификатор типов сообщений**

**Техническая реализация:**
```python
class MessageTypeClassifier:
    def __init__(self):
        self.classes = [
            'decision',    # Решение
            'question',    # Вопрос
            'information', # Информация
            'opinion',     # Мнение
            'task',        # Задача
            'casual'       # Обычное общение
        ]
        
    def classify_type(self, message: str) -> str:
        # Без обучения - правила
        if self.is_decision(message):
            return 'decision'
        elif self.is_question(message):
            return 'question'
        elif self.is_task(message):
            return 'task'
        # ... остальные правила
        
    def is_decision(self, message: str) -> bool:
        decision_patterns = [
            r'решили что',
            r'принимаем решение',
            r'утверждаем',
            r'делаем так',
            r'окончательно'
        ]
        
        return any(re.search(pattern, message.lower()) for pattern in decision_patterns)
```

**С обучением:**
- **Модель**: DistilBERT для классификации
- **Датасет**: 3K размеченных сообщений
- **Категории**: 6 классов
- **Время обучения**: 2 часа на V100
- **Качество**: 90-95% accuracy

#### **2.4 Автоматическая суммаризация**

**Self-hosted решение:**
```python
class CustomSummarizer:
    def __init__(self):
        self.model = T5ForConditionalGeneration.from_pretrained(
            "cointegrated/rut5-base-absum"
        )
        self.tokenizer = T5Tokenizer.from_pretrained(
            "cointegrated/rut5-base-absum"
        )
        
    def summarize(self, messages: List[str], max_length: int = 200) -> str:
        # Объединяем сообщения
        combined_text = " ".join(messages)
        
        # Токенизируем
        inputs = self.tokenizer(
            combined_text,
            max_length=1024,
            truncation=True,
            return_tensors="pt"
        )
        
        # Генерируем резюме
        summary_ids = self.model.generate(
            inputs["input_ids"],
            max_length=max_length,
            num_beams=4,
            early_stopping=True
        )
        
        summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
```

**API решение:**
```python
class APISummarizer:
    def __init__(self):
        self.openai_client = OpenAI()
        
    async def summarize(self, messages: List[str], max_length: int = 200) -> str:
        combined_text = "\n".join(messages)
        
        prompt = f"""
        Создай краткое резюме следующих сообщений из командного чата:
        
        {combined_text}
        
        Резюме должно быть не более {max_length} слов и содержать:
        - Основные обсуждаемые темы
        - Принятые решения
        - Важные вопросы
        """
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content
```

---

## Компонент 3: Множественные индексы

### 🎯 **Назначение**
Создание специализированных индексов для различных типов поиска и оптимизации производительности.

### 🔍 **Типы индексов**

#### **3.1 Временной индекс (Temporal Index)**

**Техническая реализация:**
```python
class TemporalIndex:
    def __init__(self):
        self.time_buckets = {
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
            'week': timedelta(weeks=1),
            'month': timedelta(days=30)
        }
        
    def create_temporal_structure(self, messages: List[Dict]) -> Dict:
        temporal_data = {}
        
        for message in messages:
            timestamp = datetime.fromisoformat(message['timestamp'])
            
            # Создаем ключи для разных временных интервалов
            hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
            day_key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            week_key = self.get_week_start(timestamp)
            
            # Группируем по интервалам
            if hour_key not in temporal_data:
                temporal_data[hour_key] = []
            temporal_data[hour_key].append(message)
            
        return temporal_data
    
    async def search_by_time(self, query: str, time_range: Tuple[datetime, datetime]) -> List[Dict]:
        start_time, end_time = time_range
        
        # Ищем в соответствующих временных блоках
        relevant_messages = []
        current_time = start_time
        
        while current_time <= end_time:
            hour_messages = await self.get_hour_messages(current_time)
            if hour_messages:
                filtered = self.filter_by_query(hour_messages, query)
                relevant_messages.extend(filtered)
            current_time += timedelta(hours=1)
            
        return relevant_messages
```

**Elasticsearch реализация:**
```python
# Mapping для временного индекса
temporal_mapping = {
    "mappings": {
        "properties": {
            "timestamp": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
            },
            "content": {
                "type": "text",
                "analyzer": "russian"
            },
            "hour_bucket": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:00:00.000'Z'"
            },
            "day_bucket": {
                "type": "date",
                "format": "yyyy-MM-dd'T'00:00:00.000'Z'"
            },
            "team_id": {
                "type": "keyword"
            }
        }
    }
}

class ElasticsearchTemporalIndex:
    def __init__(self):
        self.es_client = Elasticsearch([{'host': 'localhost', 'port': 9200}])
        self.index_name = 'messages_temporal'
        
    async def search_by_time_range(self, query: str, team_id: str, 
                                   start_time: datetime, end_time: datetime) -> List[Dict]:
        
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"content": query}},
                        {"term": {"team_id": team_id}},
                        {"range": {
                            "timestamp": {
                                "gte": start_time.isoformat(),
                                "lte": end_time.isoformat()
                            }
                        }}
                    ]
                }
            },
            "sort": [
                {"timestamp": {"order": "desc"}}
            ]
        }
        
        response = await self.es_client.search(
            index=self.index_name,
            body=search_body
        )
        
        return [hit['_source'] for hit in response['hits']['hits']]
```

#### **3.2 Тематический индекс (Topical Index)**

**Техническая реализация:**
```python
class TopicalIndex:
    def __init__(self):
        self.topic_hierarchy = {
            'development': ['backend', 'frontend', 'mobile', 'devops'],
            'product': ['features', 'design', 'testing', 'release'],
            'business': ['strategy', 'marketing', 'sales', 'finance'],
            'operations': ['meetings', 'planning', 'reviews', 'admin']
        }
        
    def build_topic_index(self, messages: List[Dict]) -> Dict[str, List[Dict]]:
        topic_index = {}
        
        for message in messages:
            # Определяем темы сообщения
            topics = self.detect_message_topics(message['content'])
            
            for topic in topics:
                if topic not in topic_index:
                    topic_index[topic] = []
                topic_index[topic].append(message)
                
        return topic_index
    
    def detect_message_topics(self, content: str) -> List[str]:
        topics = []
        content_lower = content.lower()
        
        # Ищем по ключевым словам
        for main_topic, subtopics in self.topic_hierarchy.items():
            for subtopic in subtopics:
                if subtopic in content_lower:
                    topics.append(f"{main_topic}.{subtopic}")
                    
        # Если не найдено специфичных тем, определяем общую
        if not topics:
            topics = self.classify_general_topic(content)
            
        return topics
```

**Векторный поиск с тематической группировкой:**
```python
class VectorTopicalIndex:
    def __init__(self):
        self.pinecone_client = pinecone.Index(host=settings.pinecone_host)
        self.embedding_model = OpenAIEmbeddings()
        
    async def search_by_topic(self, query: str, team_id: str, 
                             topics: List[str] = None) -> List[Dict]:
        
        # Создаем эмбеддинг для запроса
        query_embedding = await self.embedding_model.embed_query(query)
        
        # Формируем фильтры по темам
        metadata_filter = {
            "team_id": team_id
        }
        
        if topics:
            metadata_filter["topic"] = {"$in": topics}
        
        # Поиск в Pinecone
        results = self.pinecone_client.query(
            namespace=f"topical-{team_id}",
            vector=query_embedding,
            filter=metadata_filter,
            top_k=10,
            include_metadata=True
        )
        
        return [
            {
                "content": match.metadata["text"],
                "score": match.score,
                "topic": match.metadata["topic"],
                "timestamp": match.metadata["timestamp"]
            }
            for match in results.matches
        ]
```

#### **3.3 Персональный индекс (Personal Index)**

**Техническая реализация:**
```python
class PersonalIndex:
    def __init__(self):
        self.user_profiles = {}
        
    def build_personal_index(self, messages: List[Dict]) -> Dict[str, Dict]:
        personal_index = {}
        
        for message in messages:
            author = message['author']
            
            if author not in personal_index:
                personal_index[author] = {
                    'messages': [],
                    'topics': set(),
                    'sentiment': [],
                    'activity_patterns': {}
                }
            
            # Добавляем сообщение
            personal_index[author]['messages'].append(message)
            
            # Анализируем темы пользователя
            topics = self.extract_user_topics(message['content'])
            personal_index[author]['topics'].update(topics)
            
            # Анализируем настроение
            sentiment = self.analyze_sentiment(message['content'])
            personal_index[author]['sentiment'].append(sentiment)
            
            # Анализируем паттерны активности
            self.update_activity_patterns(personal_index[author], message)
            
        return personal_index
    
    def search_by_person(self, query: str, person: str, team_id: str) -> List[Dict]:
        # Поиск сообщений конкретного человека
        user_messages = self.get_user_messages(person, team_id)
        
        # Фильтруем по запросу
        relevant_messages = []
        for message in user_messages:
            if self.is_relevant(message['content'], query):
                relevant_messages.append(message)
                
        return relevant_messages
```

#### **3.4 Фактический индекс (Factual Index)**

**Техническая реализация:**
```python
class FactualIndex:
    def __init__(self):
        self.fact_extractors = {
            'decisions': DecisionExtractor(),
            'dates': DateExtractor(),
            'numbers': NumberExtractor(),
            'tasks': TaskExtractor(),
            'links': LinkExtractor()
        }
        
    def extract_facts(self, message: Dict) -> List[Dict]:
        facts = []
        content = message['content']
        
        # Извлекаем разные типы фактов
        for fact_type, extractor in self.fact_extractors.items():
            extracted = extractor.extract(content)
            
            for fact in extracted:
                facts.append({
                    'type': fact_type,
                    'value': fact['value'],
                    'context': fact['context'],
                    'message_id': message['id'],
                    'timestamp': message['timestamp'],
                    'author': message['author']
                })
                
        return facts
    
    def search_facts(self, query: str, fact_types: List[str] = None) -> List[Dict]:
        # Поиск только по фактам
        search_results = []
        
        for fact in self.fact_database:
            if fact_types and fact['type'] not in fact_types:
                continue
                
            if self.matches_query(fact, query):
                search_results.append(fact)
                
        return search_results
```

**Экстракторы фактов:**
```python
class DecisionExtractor:
    def __init__(self):
        self.decision_patterns = [
            r'решили (.+)',
            r'принимаем решение (.+)',
            r'утверждаем (.+)',
            r'договорились (.+)'
        ]
        
    def extract(self, text: str) -> List[Dict]:
        decisions = []
        
        for pattern in self.decision_patterns:
            matches = re.finditer(pattern, text.lower())
            
            for match in matches:
                decisions.append({
                    'value': match.group(1),
                    'context': match.group(0),
                    'confidence': 0.9
                })
                
        return decisions

class DateExtractor:
    def __init__(self):
        self.date_patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',  # 15.01.2024
            r'(\d{1,2} \w+ \d{4})',        # 15 января 2024
            r'(завтра|послезавтра|сегодня)',
            r'через (\d+) (дн|недел|месяц)'
        ]
        
    def extract(self, text: str) -> List[Dict]:
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text.lower())
            
            for match in matches:
                parsed_date = self.parse_date(match.group(1))
                if parsed_date:
                    dates.append({
                        'value': parsed_date,
                        'context': match.group(0),
                        'confidence': 0.85
                    })
                    
        return dates
```

---

## Компонент 4: Динамический контекст

### 🎯 **Назначение**
Интеллектуальное формирование контекста под каждый конкретный запрос с оптимизацией использования токенов.

### 🧠 **Анализатор вопросов**

**Техническая реализация:**
```python
class QuestionAnalyzer:
    def __init__(self):
        self.question_types = {
            'factual': ['кто', 'что', 'где', 'когда', 'сколько'],
            'procedural': ['как', 'каким образом', 'способ'],
            'causal': ['почему', 'из-за чего', 'причина'],
            'temporal': ['когда', 'во сколько', 'до когда'],
            'comparative': ['лучше', 'хуже', 'сравни'],
            'summary': ['резюме', 'итоги', 'обзор', 'summary']
        }
        
    def analyze_question(self, question: str) -> Dict:
        analysis = {
            'type': self.detect_question_type(question),
            'entities': self.extract_entities(question),
            'time_scope': self.detect_time_scope(question),
            'context_requirements': self.assess_context_needs(question),
            'priority_sources': self.determine_priority_sources(question)
        }
        
        return analysis
    
    def detect_question_type(self, question: str) -> str:
        question_lower = question.lower()
        
        for q_type, keywords in self.question_types.items():
            if any(keyword in question_lower for keyword in keywords):
                return q_type
                
        return 'general'
    
    def detect_time_scope(self, question: str) -> str:
        time_indicators = {
            'recent': ['сейчас', 'сегодня', 'недавно', 'последние'],
            'specific': ['вчера', 'на прошлой неделе', 'в понедельник'],
            'period': ['за месяц', 'за неделю', 'за год'],
            'all_time': ['всегда', 'за все время', 'история']
        }
        
        question_lower = question.lower()
        
        for scope, indicators in time_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                return scope
                
        return 'general'
```

### 📊 **Сборщик контекста**

**Техническая реализация:**
```python
class ContextBuilder:
    def __init__(self):
        self.max_context_tokens = 3000
        self.context_sources = {
            'live': LiveContextSource(),
            'daily': DailySummarySource(),
            'topical': TopicalIndexSource(),
            'personal': PersonalIndexSource(),
            'factual': FactualIndexSource()
        }
        
    async def build_context(self, question: str, team_id: str, 
                           question_analysis: Dict) -> Dict:
        
        context_parts = []
        remaining_tokens = self.max_context_tokens
        
        # Определяем стратегию сбора контекста
        strategy = self.determine_context_strategy(question_analysis)
        
        # Собираем контекст по приоритету
        for source_name, priority in strategy.items():
            if remaining_tokens <= 0:
                break
                
            source = self.context_sources[source_name]
            source_context = await source.get_context(
                question, team_id, question_analysis, remaining_tokens
            )
            
            if source_context:
                context_parts.append({
                    'source': source_name,
                    'priority': priority,
                    'content': source_context['content'],
                    'tokens_used': source_context['tokens']
                })
                
                remaining_tokens -= source_context['tokens']
        
        # Оптимизируем итоговый контекст
        optimized_context = self.optimize_context(context_parts)
        
        return optimized_context
    
    def determine_context_strategy(self, analysis: Dict) -> Dict[str, int]:
        question_type = analysis['type']
        time_scope = analysis['time_scope']
        
        # Базовая стратегия
        strategy = {
            'live': 1,
            'daily': 2,
            'topical': 3,
            'personal': 4,
            'factual': 5
        }
        
        # Корректируем под тип вопроса
        if question_type == 'factual':
            strategy['factual'] = 1
            strategy['live'] = 2
            
        elif question_type == 'temporal':
            if time_scope == 'recent':
                strategy['live'] = 1
            elif time_scope == 'specific':
                strategy['daily'] = 1
                
        elif question_type == 'summary':
            strategy['daily'] = 1
            strategy['topical'] = 2
            
        return strategy
```

### 🔧 **Компрессор контекста**

**Техническая реализация:**
```python
class ContextCompressor:
    def __init__(self):
        self.compression_strategies = {
            'summarization': SummarizationCompressor(),
            'extraction': ExtractionCompressor(),
            'filtering': FilteringCompressor(),
            'clustering': ClusteringCompressor()
        }
        
    def compress_context(self, context_parts: List[Dict], 
                        target_tokens: int) -> Dict:
        
        total_tokens = sum(part['tokens_used'] for part in context_parts)
        
        if total_tokens <= target_tokens:
            return self.merge_context_parts(context_parts)
        
        # Выбираем стратегию компрессии
        compression_ratio = target_tokens / total_tokens
        
        if compression_ratio > 0.7:
            # Легкая компрессия - фильтрация
            compressed = self.compression_strategies['filtering'].compress(
                context_parts, target_tokens
            )
        elif compression_ratio > 0.4:
            # Средняя компрессия - извлечение ключевых частей
            compressed = self.compression_strategies['extraction'].compress(
                context_parts, target_tokens
            )
        else:
            # Сильная компрессия - суммаризация
            compressed = self.compression_strategies['summarization'].compress(
                context_parts, target_tokens
            )
            
        return compressed

class SummarizationCompressor:
    def __init__(self):
        self.summarizer = T5ForConditionalGeneration.from_pretrained(
            "cointegrated/rut5-base-absum"
        )
        
    def compress(self, context_parts: List[Dict], target_tokens: int) -> Dict:
        # Группируем похожие части
        grouped_parts = self.group_similar_parts(context_parts)
        
        compressed_parts = []
        tokens_used = 0
        
        for group in grouped_parts:
            if tokens_used >= target_tokens:
                break
                
            # Суммаризируем группу
            group_text = " ".join([part['content'] for part in group])
            summary = self.summarize_text(group_text, max_length=200)
            
            summary_tokens = len(summary.split())
            if tokens_used + summary_tokens <= target_tokens:
                compressed_parts.append({
                    'content': summary,
                    'tokens': summary_tokens,
                    'compression_ratio': len(group_text) / len(summary)
                })
                tokens_used += summary_tokens
                
        return {
            'content': compressed_parts,
            'total_tokens': tokens_used,
            'compression_method': 'summarization'
        }
```

### ✅ **Валидатор ответов**

**Техническая реализация:**
```python
class AnswerValidator:
    def __init__(self):
        self.validation_criteria = {
            'relevance': RelevanceValidator(),
            'completeness': CompletenessValidator(),
            'accuracy': AccuracyValidator(),
            'coherence': CoherenceValidator()
        }
        
    async def validate_answer(self, question: str, answer: str, 
                            context: Dict) -> Dict:
        
        validation_results = {}
        
        # Проверяем по всем критериям
        for criterion, validator in self.validation_criteria.items():
            score = await validator.validate(question, answer, context)
            validation_results[criterion] = score
            
        # Общая оценка
        overall_score = sum(validation_results.values()) / len(validation_results)
        
        # Определяем, нужно ли улучшать ответ
        needs_improvement = overall_score < 0.7
        
        return {
            'scores': validation_results,
            'overall_score': overall_score,
            'needs_improvement': needs_improvement,
            'suggestions': self.generate_improvement_suggestions(validation_results)
        }

class RelevanceValidator:
    def __init__(self):
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    async def validate(self, question: str, answer: str, context: Dict) -> float:
        # Проверяем семантическую близость
        question_embedding = self.similarity_model.encode(question)
        answer_embedding = self.similarity_model.encode(answer)
        
        similarity = cosine_similarity([question_embedding], [answer_embedding])[0][0]
        
        # Проверяем, отвечает ли ответ на вопрос
        contains_answer = self.contains_direct_answer(question, answer)
        
        # Итоговая оценка
        relevance_score = (similarity * 0.6) + (contains_answer * 0.4)
        
        return relevance_score
```

---

## Интеграция и оркестрация

### 🎭 **Основной оркестратор**

**Техническая реализация:**
```python
class RAGOrchestrator:
    def __init__(self):
        self.hierarchical_context = HierarchicalContextManager()
        self.data_processor = DataPreprocessor()
        self.multi_index = MultiIndexManager()
        self.dynamic_context = DynamicContextBuilder()
        
    async def process_question(self, question: str, team_id: str, 
                              user_id: str) -> Dict:
        
        # Этап 1: Анализ вопроса
        question_analysis = await self.analyze_question(question)
        
        # Этап 2: Определение стратегии поиска
        search_strategy = self.determine_search_strategy(question_analysis)
        
        # Этап 3: Сбор контекста
        context = await self.build_optimized_context(
            question, team_id, question_analysis, search_strategy
        )
        
        # Этап 4: Генерация ответа
        answer = await self.generate_answer(question, context)
        
        # Этап 5: Валидация и улучшение
        validation = await self.validate_answer(question, answer, context)
        
        if validation['needs_improvement']:
            # Улучшаем ответ
            improved_answer = await self.improve_answer(
                question, answer, context, validation['suggestions']
            )
            answer = improved_answer
            
        # Этап 6: Логирование и обучение
        await self.log_interaction(question, answer, context, validation)
        
        return {
            'answer': answer,
            'confidence': validation['overall_score'],
            'context_used': context['summary'],
            'processing_time': context['processing_time']
        }
```

---

## Стратегия обучения и fine-tuning

### 🎓 **Что нужно обучать**

#### **1. Классификатор важности сообщений**
- **Необходимость**: Высокая
- **Данные**: 5K размеченных сообщений
- **Время**: 4-6 часов
- **Стоимость**: $100-150
- **Улучшение**: +15% точности

#### **2. Экстрактор сущностей**
- **Необходимость**: Средняя
- **Данные**: 3K сообщений с размеченными сущностями
- **Время**: 6-8 часов
- **Стоимость**: $200-300
- **Улучшение**: +20% точности

#### **3. Модель суммаризации**
- **Необходимость**: Высокая
- **Данные**: 2K пар (сообщения -> резюме)
- **Время**: 8-12 часов
- **Стоимость**: $300-500
- **Улучшение**: +25% качества

### 🚀 **Что можно использовать без обучения**

#### **1. Временной и тематический поиск**
- **Готовые решения**: Elasticsearch, Pinecone
- **Качество**: 80-85%
- **Время внедрения**: 1-2 недели

#### **2. Базовая классификация типов сообщений**
- **Подход**: Правила + простые модели
- **Качество**: 70-75%
- **Время внедрения**: 3-5 дней

#### **3. Персональный поиск**
- **Подход**: Фильтрация по автору + семантический поиск
- **Качество**: 75-80%
- **Время внедрения**: 1 неделя

### 📈 **Постепенное улучшение**

#### **Этап 1: Минимальный MVP (без обучения)**
- Простые правила для классификации
- Базовый поиск по индексам
- Готовые модели для эмбеддингов
- **Время**: 4-6 недель
- **Качество**: 70-75%

#### **Этап 2: Улучшенная версия (частичное обучение)**
- Fine-tuned классификатор важности
- Кастомный экстрактор сущностей
- **Время**: +2-3 недели
- **Качество**: 80-85%

#### **Этап 3: Продвинутая версия (полное обучение)**
- Все компоненты обучены на домене
- Оптимизированные модели
- **Время**: +3-4 недели
- **Качество**: 85-90%

### 💡 **Рекомендации по внедрению**

1. **Начните с MVP**: Используйте готовые решения для быстрого старта
2. **Собирайте данные**: Параллельно накапливайте данные для обучения
3. **Итеративное улучшение**: Постепенно заменяйте компоненты на обученные
4. **Мониторинг качества**: Постоянно отслеживайте метрики
5. **Пользовательские фидбеки**: Используйте отзывы для улучшения

**Итоговая рекомендация**: Начните с базовой версии без обучения, которая даст 70-75% качества, а затем постепенно улучшайте компоненты через fine-tuning для достижения 85-90% качества. 
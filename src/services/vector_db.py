from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import logging
import uuid
import asyncio

from src.settings import settings

# Initialize local embedding model
try:
    # Используем многоязычную модель для русского языка
    embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    logging.info("✅ Local embedding model loaded successfully")
except Exception as e:
    logging.error(f"❌ Failed to load embedding model: {e}")
    embedding_model = None

# Initialize Pinecone
pc = Pinecone(api_key=settings.pinecone_api_key.get_secret_value())
pinecone_index = pc.Index(host=settings.pinecone_host)


async def get_embedding(text: str, model="local"):
    """
    Создает эмбеддинг для текста используя локальную модель
    """
    if embedding_model is None:
        raise Exception("Embedding model not loaded")
    
    try:
        # Очищаем текст
        text = text.replace("\n", " ").strip()
        
        # Создаем эмбеддинг в отдельном потоке (модель синхронная)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, embedding_model.encode, text)
        
        # Возвращаем как список
        return embedding.tolist()
        
    except Exception as e:
        logging.error(f"❌ Failed to create embedding: {e}")
        raise e

def upsert_vector(vector_id: str, vector: list, team_id: str, text: str):
    """Upsert vector to Pinecone with team namespace"""
    namespace = f"team-{team_id}"
    
    try:
        logging.info(f"Upserting vector {vector_id} to namespace: {namespace}")
        
        pinecone_index.upsert(
            vectors=[{
                "id": vector_id,
                "values": vector,
                "metadata": {"text": text}
            }],
            namespace=namespace
        )
        
        logging.info(f"Successfully upserted vector {vector_id} to namespace {namespace}")
        
    except Exception as e:
        logging.error(f"Failed to upsert vector {vector_id} to namespace {namespace}: {e}", exc_info=True)
        raise e

def get_namespace_stats(team_id: str):
    """Get statistics for a team namespace"""
    namespace = f"team-{team_id}"
    
    try:
        logging.info(f"Getting stats for namespace: {namespace}")
        stats = pinecone_index.describe_index_stats()
        
        namespace_stats = stats.get('namespaces', {}).get(namespace, {})
        vector_count = namespace_stats.get('vector_count', 0)
        
        logging.info(f"Namespace {namespace} has {vector_count} vectors")
        return {
            'namespace': namespace,
            'vector_count': vector_count,
            'exists': vector_count > 0
        }
        
    except Exception as e:
        logging.error(f"Failed to get stats for namespace {namespace}: {e}", exc_info=True)
        return {
            'namespace': namespace,
            'vector_count': 0,
            'exists': False,
            'error': str(e)
        }

async def test_team_vector_creation(team_id: str, test_text: str = "Тестовое сообщение для проверки создания namespace"):
    """Test function to manually create a vector for a team"""
    try:
        logging.info(f"Testing vector creation for team {team_id}")
        
        # Create embedding
        vector = await get_embedding(test_text)
        
        # Create unique ID
        vector_id = f"test-{str(uuid.uuid4())}"
        
        # Upsert to Pinecone
        upsert_vector(vector_id, vector, team_id, test_text)
        
        # Get stats
        stats = get_namespace_stats(team_id)
        
        logging.info(f"Test completed for team {team_id}. Stats: {stats}")
        return {
            'success': True,
            'vector_id': vector_id,
            'stats': stats
        }
        
    except Exception as e:
        logging.error(f"Test failed for team {team_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


async def test_embedding_service():
    """
    Тестирует сервис эмбеддингов
    """
    try:
        test_text = "Привет! Это тестовое сообщение для проверки эмбеддингов."
        
        logging.info("🧪 Testing embedding service...")
        embedding = await get_embedding(test_text)
        
        if len(embedding) > 0:
            logging.info(f"✅ Embedding created successfully! Size: {len(embedding)}")
            return {
                'success': True,
                'embedding_size': len(embedding),
                'model': 'paraphrase-multilingual-MiniLM-L12-v2'
            }
        else:
            logging.error("❌ Empty embedding returned")
            return {
                'success': False,
                'error': 'Empty embedding'
            }
            
    except Exception as e:
        logging.error(f"❌ Embedding test failed: {e}")
        return {
            'success': False,
            'error': str(e)
        } 
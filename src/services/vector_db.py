from openai import AsyncOpenAI
from pinecone import Pinecone
import logging
import uuid

from src.settings import settings

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

# Initialize Pinecone
pc = Pinecone(api_key=settings.pinecone_api_key.get_secret_value())
pinecone_index = pc.Index(host=settings.pinecone_host)


async def get_embedding(text: str, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    response = await client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

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
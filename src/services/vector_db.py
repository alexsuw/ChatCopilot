from openai import AsyncOpenAI
from pinecone import Pinecone

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

def upsert_vector(vector_id: str, vector: list, team_id: int, text: str):
    pinecone_index.upsert(
        vectors=[{
            "id": vector_id,
            "values": vector,
            "metadata": {"text": text}
        }],
        namespace=f"team-{team_id}"
    ) 
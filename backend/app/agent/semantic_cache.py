import redis
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.search.result import Result
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import cast
import numpy as np
import json
import hashlib
import os

INDEX_NAME = "tavily_cache_idx"
PREFIX = "tavily_cache:"
VECTOR_DIM = 768
#cosine similarity
SIMILARITY_THRESHOLD = 0.92

embeddings_model = GoogleGenerativeAIEmbeddings(model = "models/embedding-001")
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is not set")
redis_client = redis.from_url(REDIS_URL, decode_responses = False)

def _ensure_index():
    """
    Creates the RedisSearch vector index if it doesn't exist yet.
    Safe to call at every startup - checks existence first
    """

    try:
        redis_client.ft(INDEX_NAME).info()
        #if index exists already
        return
    except redis.ResponseError:
        #index doesn't exist
        pass

    #Defining the schema for the caching
    schema = (
        TextField("query_text"),
        TextField("result_json"),
        VectorField(
            "embedding",
            "FLAT",
            {
                "Type": "FLOAT32",
                "DIM": VECTOR_DIM,
                "DISTANCE_METRIC": "COSINE",
            },
        ),
    )

    definition = IndexDefinition(prefix = [PREFIX], index_type = IndexType.HASH)
    redis_client.ft(INDEX_NAME).create_index(fields = schema, definition=definition)
    print(f"Created RedisSearch index:{INDEX_NAME}")

def _embed(text: str)->np.ndarray:
    """
    Converts text into a 768-dim embedding vector using Google's model.
    """
    vector = embeddings_model.embed_query(text)
    return np.array(vector, dtype=np.float32)

def get_cached_search(query: str)->list|None:
    """
    Checks Redis for a semantically similar past quert.
    Returns cached search results if similarity is above threshold else None.
    """
    _ensure_index()

    query_vector = _embed(query)
    vector_bytes = query_vector.tobytes()

    redis_query = (
        Query(f"*=>[KNN 1 @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("query_text", "result_json", "score")
        .dialect(2)
    )

    try:
        raw_results = redis_client.ft(INDEX_NAME).search(
            redis_query, query_params = {"vec": vector_bytes}
        )
        results = cast(Result, raw_results)

    except Exception as e:
        print(f"Semantic cache search error: {e}")
        return None

    if not results.docs:
        return None
    
    top_match = results.docs[0]
    #Cosine Similarity based on distance in RedisSearch: 0 = identical, 2 = opposite
    distance = float(top_match.score)
    similarity = 1 - (distance/2)

    if similarity >= SIMILARITY_THRESHOLD:
        print(f"Cache HIT- similarity {similarity:.3f} for query: '{query}'")
        return json.loads(top_match.results_json)
    
    print(f"Cache MISS - best similarity {similarity:.3f} for query: '{query}'")
    return None

def save_to_cache(query: str, results: list)-> None:
    """
    Stores a new query + its Tavily results in the semantic cache.
    """ 
    _ensure_index()

    query_vector = _embed(query)
    key = PREFIX + hashlib.sha256(query.encode()).hexdigest()

    redis_client.hset(
        key,
        mapping = {
            "query_text": query,
            "result_json": json.dumps(results),
            "embedding": query_vector.tobytes(),
        },
    )
    
    #Expiring cache after 7 days so that it doesn't become stale 
    redis_client.expire(key, 60 * 60 *24 * 7)

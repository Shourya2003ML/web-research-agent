from mem0 import MemoryClient
import os

mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

#Retrieving the memories
def retrieve_memories(query: str, user_id: str)->str:
    """
    Search mem0 for relevant facts about the user based on the query
    Returns a formatted string to inject into the system prompt
    Returns empty string if nothing relevant is found
    """

    try:
        response = mem0_client.search(query = query,
                                    filters = {"user_id": user_id},
                                    limit=5,)
        
        print(f"DEBUG Mem0 response type: {type(response)}, value: {response}")

        if isinstance(response, dict):
            results = response.get("results", [])
        else:
            results = response

        if not results:
            return ""

        memories = [r["memory"] for r in results if isinstance(r, dict) and "memory" in r]

        if not memories:
            return ""

        return "Known facts about this user: \n" + "\n".join(f"- {m}" for m in memories)
 
    except Exception as e:
        print(f"Mem0 retrieval error: {e}")
        return "" 

#saving the interactions per user
def save_interaction(user_message: str, ai_message: str, user_id: str)->None:
    """
    Saves the latest exchange to Mem0. Mem0 automatically extracts facts/preferences
    from the raw conversations
    """
    try:
        mem0_client.add(
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assisstant", "content": ai_message},
            ],
            user_id = user_id,
        )
    except Exception as e:
        print(f"Mem0 save error : {e}")
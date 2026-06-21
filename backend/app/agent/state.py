from typing import TypedDict, Annotated, List
from langgraph.graph import add_messages #Using add reducer

#defining the state schema
class ResearchState(TypedDict):
    """
    Shared state that flows through the every node. 'messages' uses add_message reducer
    to cumulate the messages rather than overwriting
    """
    messages: Annotated[list, add_messages]
    query: str
    search_results: List[dict]
    needs_search: bool 
    summary: str
    user_id: str
    memory_context: str
#Building and Compiling Graph
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import StateGraph, START, END
from app.agent.state import ResearchState
from app.agent.nodes import (retrieve_memory_node, router_node, search_node, summarize_node, respond_node, route_decision)
import os

#Building the graph
async def build_graph():
    """
    Assembling the graph using LangGraph StateGraph.
    Using Sqlite3 for checkpointing (Short Term Memory) for thread level persistence
    Use .invoke() and .stream() for invoking and streaming using LangGraph.
    Using Async graph builder - must be awaited
    AsyncSqliteSaver requires async context manager
    """

    redis_url = os.getenv("REDIS_URL");

    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
    
    #AsyncRedisSaver for connection pooling 
    checkpointer = AsyncRedisSaver(redis_url=redis_url)

    #Initialzing the connection 
    await checkpointer.asetup()

    #Intializing the Graph
    graph = StateGraph(ResearchState)

    #Adding Nodes
    graph.add_node("retrieve_memory", retrieve_memory_node)
    graph.add_node("router", router_node)
    graph.add_node("search", search_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("respond", respond_node)

    #Adding Edges
    graph.add_edge(START, "retrieve_memory")
    graph.add_edge("retrieve_memory", "router")

    graph.add_conditional_edges(
        "router",
        route_decision,{
            "search": "search",
            "respond": "respond",
        }
    )
    graph.add_edge("search", "summarize")
    graph.add_edge("summarize", "respond")
    graph.add_edge("respond", END)

    #Compiling the graph with checkpointers
    return graph.compile(checkpointer = checkpointer)

#compiled_graph = build_graph()




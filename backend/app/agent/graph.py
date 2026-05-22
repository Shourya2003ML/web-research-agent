#Building and Compiling Graph
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.state import ResearchState
from app.agent.nodes import (router_node, search_node, summarize_node, respond_node, route_decision)
import os
import aiosqlite

#Building the graph
async def build_graph():
    """
    Assembling the graph using LangGraph StateGraph.
    Using Sqlite3 for checkpointing (Short Term Memory) for thread level persistence
    Use .invoke() and .stream() for invoking and streaming using LangGraph.
    Using Async graph builder - must be awaited
    AsyncSqliteSaver requires async context manager
    """

    #Establishing the sql connection
    db_path = os.getenv("SQLITE_DB_PATH", "data/checkpointers.db")

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok = True)
    
    conn = await aiosqlite.connect(db_path)
    checkpointer =  AsyncSqliteSaver(conn)


    #Intializing the Graph
    graph = StateGraph(ResearchState)

    #Adding Nodes
    graph.add_node("router", router_node)
    graph.add_node("search", search_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("respond", respond_node)

    #Adding Edges
    graph.add_edge(START, "router")
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




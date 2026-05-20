#Building and Compiling Graph
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from app.agent.state import ResearchState
from app.agent.nodes import (router_node, search_node, summarize_node, respond_node, route_decision)
import sqlite3
import os

#Building the graph
def build_graph():
    """
    Assembling the graph using LangGraph StateGraph.
    Using Sqlite3 for checkpointing (Short Term Memory) for thread level persistence
    Use .invoke() and .stream() for invoking and streaming using LangGraph.
    """

    #Establishing the sql connection
    db_path = os.getenv("SQL_DB_PATH", "data/checkpointers.db")
    conn = sqlite3.connect(db_path, check_same_thread = False)
    checkpointer = SqliteSaver(conn)

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

compiled_graph = build_graph()




import chainlit as cl
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import uuid
import sys
import os
from pathlib import Path

#Importing backend
#sys.path.append('/backend/app/agent')

sys.path.insert(0, "/backend")


from app.agent.graph import build_graph 
load_dotenv()

#root_path = Path(__file__).resolve().parent.parent
#sys.path.append(str(root_path))

#from backend.app.agent.graph import build_graph

#Chat starters giving suggestions 
@cl.set_starters
async def set_starters(user: cl.User | None = None, chat_profile: str | None = None):
    return [
        cl.Starter(
            label = "Latest AI News",
            message = "What are the most import AI developments this week?",
        ),
        cl.Starter(
            label = "Explain a concept",
            message = "Explain how langgraph's checkpointing works in simple terms",
        ),
        cl.Starter(
            label = "Quick Search",
            message = "Give me 3 point summary of the current state of fusion energy.",
        ),
    ]

#on starting of the chat
@cl.on_chat_start
async def on_chat_start():
    """
    Default text that shows before new chat begins
    Building the graph and storing for the current session.
    """
    thread_id = str(uuid.uuid4())
    graph = await build_graph()

    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("graph", graph)

    await cl.Message(
        content = (
            "👋 Hello! I'm your **Agentic Web Research Assistant**.\n\n"
            "Ask me anything — I'll search the web, summarise results, "
            "and remember our entire conversation."
        )
    ).send()


#when message has been sent
@cl.on_message
async def on_message(message: cl.Message):
    """
    Called everytime the user sends a message.
    Streaming the langgraph response with steps
    """

    graph = cl.user_session.get("graph")
    thread_id = cl.user_session.get("thread_id")

    if graph is None or thread_id is None:
        await cl.Message(content = "Session not initalized. Please refresh the page.").send()
        return 
    
    config = {"configurable": {"thread_id": thread_id}}

    node_labels = {
        "router":    "Routing query",
        "search":    "Searching the web",
        "summarise": "Summarising results",
        "respond":   "Composing answer",
    }

    #Empty message bubbles to stream into
    answer_msg = cl.Message(content="")
    await answer_msg.send()

    current_step = None
    final_content = ""

    try:
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content = message.content)]},
            config = config,
        ):
            kind = event["event"]
            name = event.get("name", "")

            #open side panel when new node start
            if kind == "on_chain_start" and name in node_labels:
                #current_step = cl.Step(name = node_labels[name])
                #await current_step.__aenter__()
                async with cl.Step(name=node_labels[name]):
                    pass


            #Close side panel when the node finish
            if kind == "on_chain_end" and name in node_labels:
                output = event.get("data", {}).get("output", {})
                messages = output.get("messages", [])
                if messages:
                    final_content = messages[-1].content
                """
                if current_step:
                    #show output in step panel
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        if output.get("needs_search") is not None:
                            current_step.output = (
                                "will search web" if output["needs_search"]
                                else "Answering from memory"
                            )
                        elif output.get("search results"):
                            current_step.output = (
                                f"Found {len(output['search_results'])} results"
                            )
                        elif output.get("summary"):
                            current_step.output = "Summary Ready"
                    await current_step.__aexit__(None, None, None)
                    current_step = None
                """

            #Streaming tokens from the final respod node's LLM
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await answer_msg.stream_token(chunk.content)
                """
                tags = event.get("tags", [])
                if "final_answer" in tags:
                    chunk = event["data"].get("chunk")
                    if chunk and chunk.content:
                        await answer_msg.stream_token(chunk.content)
                """

    except Exception as e:
        await answer_msg.stream_token(f"\n\nError: {str(e)}")

    if not answer_msg.content and final_content:
        answer_msg.content = final_content

    await answer_msg.update()


#On stopping
@cl.on_stop
async def on_stop():
    """
    When user clicks the stop button
    """
    await cl.Message(content = "Task stopped. Send a new message to continue.").send()

#on chat end
@cl.on_chat_end
async def on_chat_end():
    """
    Cleanup when chat session ended with the user.
    """
    graph = cl.user_session.get("graph")
    if graph and hasattr(graph, "checkpointer"):
        checkpointer = graph.checkpointer
        if hasattr(checkpointer, "conn"):
            await checkpointer.conn.close()
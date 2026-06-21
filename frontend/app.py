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
    user_id = "shourya-demo-user"

    graph = await build_graph()

    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("graph", graph)

    await cl.Message(
        content = (
            "Hello! I'm your **Agentic Web Research Assistant**.\n\n"
            "Ask me anything — I'll search the web, summarise results, "
            "and remember our entire conversation."
        )
    ).send()


#when message has been sent
@cl.on_message
async def on_message(message: cl.Message):
    graph     = cl.user_session.get("graph")
    user_id = cl.user_session.get("user_id")
    thread_id = cl.user_session.get("thread_id")

    if graph is None or thread_id is None:
        await cl.Message(content="Session not initialised. Please refresh.").send()
        return

    config = {"configurable": {"thread_id": thread_id}}

    node_labels = {
        "retrieve_memory": "Recalling what I know already",
        "router":     "Routing query",
        "search":     "Searching the web",
        "summarize":  "Summarising results",
        "respond":    "Composing answer",
    }

    answer_msg = cl.Message(content="")
    await answer_msg.send()

    final_content = ""
    streamed_content = ""

    try:
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=message.content)], "user_id": user_id},
            config=config,
        ):
            kind = event["event"]
            name = event.get("name", "")

            # Show a Step panel for each node
            if kind == "on_chain_start" and name in node_labels:
                async with cl.Step(name=node_labels[name]):
                    pass

            #Search node for cache
            if kind == "on_chain_end" and name == "search":
                output = event.get("data", {}).get("output", {})
                if output.get("cache_hit"):
                    async with cl.Step(name = "Found in cache"):
                        pass
                else:
                    async with cl.Step(name= "Searched the web"):
                        pass

            # Only capture final state from the respond node specifically
            if kind == "on_chain_end" and name == "respond":
                output = event.get("data", {}).get("output", {})
                messages = output.get("messages", [])
                if messages:
                    final_content = messages[-1].content

            # Stream tokens only from final_answer tagged LLM calls
            if kind == "on_chat_model_stream":
                tags = event.get("tags", [])
                if "final_answer" in tags:
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        await answer_msg.stream_token(chunk.content)
                        streamed_content += chunk.content

    except Exception as e:
        await answer_msg.stream_token(f"\n\nError: {str(e)}")

    # Only use final_content fallback if nothing was streamed
    if not streamed_content and final_content:
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
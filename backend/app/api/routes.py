#fasapi routes
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.agent.graph import compiled_graph
import json

from typing import cast
from app.agent.state import ResearchState

router = APIRouter()

#ChatRequest
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default" #thread used to uniquely identify conversations

#Non streaming endpoint used for testing
@router.post("/chat")
async def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    result = compiled_graph.invoke(
        cast(ResearchState, {"messages": [HumanMessage(content = req.message)]}),
        config = config,
    )
    last_msg = result["messages"][-1]
    return {"response": last_msg.content, "thread_id": req.thread_id}

#Streaming endpoint
@router.post("/stream")
async def stream_chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    async def event_generator():
        for chunk in compiled_graph.stream(
            cast(ResearchState, {"messages": [HumanMessage(content = req.message)]}),
            config = config,
            stream_mode = "updates",
        ):
            for node_name, node_output in chunk.items():
                if "messages" in node_output:
                    msg = node_output["messages"][-1]
                    payload = {"node": node_name, "content": msg.content}
                    yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type = "text/event-stream")

#Health Check
@router.get("/health")
async def health():
    return {"status": "ok"}
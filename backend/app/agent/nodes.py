#Defining Nodes
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agent.tools import tavily_search
from app.agent.state import ResearchState
from app.agent.memory import retrieve_memories, save_interaction
import os

#initializing the llm
llm = ChatGoogleGenerativeAI(model = os.getenv("MODEL_NAME"), temperature = 0, streaming = True,)

#Node 1: Retriever we check our memory firstly
def retrieve_memory_node(state: ResearchState)->dict:
    """
    Fetches the relevant long-term facts about this user before routing
    """
    last_message = state["messages"][-1]
    user_id = state.get("user_id", "anonymous")

    memory_context = retrieve_memories(last_message.content, user_id)
    return {"memory_context": memory_context}

#Node 2: Router
def router_node (state: ResearchState) -> dict:
    """
    Decides if we want a web search. Looks at the last message in the 
    conversation history. Returns needs_search = True or False
    """

    #we look at memory context
    memory_note = state.get("memory_context", "")
    system_content = """You are a routing assistant. Decide if the user's
                        question requires a web search or can be answered using existing
                        conversation history. Reply with ONLY one word: 'search' or 'recall'."""

    #Checking memory
    if memory_note:
        system_content += f"\n\n{memory_note}"

    system = SystemMessage(content = system_content)
    last_message = state["messages"][-1]
    #using new invocation to avoid leaking to history messages
    response = llm.invoke([system, last_message])
    needs_search = "search" in response.content.lower()

    return {"needs_search": needs_search, "query": last_message.content,}

#Node 3: Search
def search_node(state: ResearchState)->dict:
    """
    Calls Tavily and stores raw results in state
    """
    results = tavily_search.invoke(state["query"])
    return {"search_results": results}

#Node 4: Summarize
def summarize_node(state: ResearchState)->dict:
    """
    Make the search results in readable format
    """
    raw = state["search_results"]

    #Handling list and string due to tavily version conflict
    if isinstance(raw, str):
        results_text = raw
    elif isinstance(raw, list):
        results_text = "\n\n".join([f"Source: {r.get('url', 'N/A')}\nContent: {r.get('content', '')}" for r in state["search_results"]])
    else:
        results_text = str(raw)
    system = SystemMessage(content = 
                        """
                            Summarize the following search results into a clear, concise answer.
                            Include source URLs as footnotes.
                        """)
    human = HumanMessage(content = f"Query: {state['query']}\n\nResults:\n{results_text}")
    response = llm.invoke([system, human])
    return {"summary": response.content}

#Node 5: Respond
def respond_node(state: ResearchState)-> dict:
    """
    Generates the final answer to send back to the user.
    """

    tagged_llm = llm.with_config(tags = ["final_answer"])
    memory_note = state.get("memory_context", "")
    user_id = state.get("user_id", "anonymous")

    #If we searched then we use summary, otherwise we will use history
    if state.get("summary"):
        #wrapping the summary
        system_content = "Present the following research summary clearly to the user."
        
        #Checking memory
        if memory_note:
            system_content += f"\n\n{memory_note}"
        
        system = SystemMessage(content = system_content)
        human = HumanMessage(content = state["summary"])
        response = tagged_llm.invoke([system, human])
        content = response.content
    else:
        system_content = "Answer user's query using the conversation history"

        #Checking memory
        if memory_note:
            system_content += f"\n\n{memory_note}"
        
        system = SystemMessage(content = system_content)
        
        #tagging so that chainlit can filter its stream events
        response = tagged_llm.invoke([system] + state["messages"])
        content = response.content

    #saving the conversation for later reference in future sessions
    last_user_message = state["messages"][-1].content()
    save_interaction(last_user_message, content, user_id)
    ai_message = AIMessage(content = content)
    return {"messages": [ai_message], "summary": ""}


#Defining the conditional edge function
def route_decision(state: ResearchState) -> str:
    """
    Used by the conditonal edges after the Router node.
    """
    return "search" if state["needs_search"] else "respond"

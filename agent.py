from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, RemoveMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END

memory = MemorySaver()

# Unified state class handling both summary and tool invocation signals
class CombinedState(MessagesState):
    summary: str

# Models capable of handling summarization and tool invocation
model = ChatAnthropic(model_name="claude-3-haiku-20240307")
model_with_tools = ChatAnthropic(model_name="model-tool-capable")

# Logic to handle model invocation (conversation node)
def handle_conversation(state: CombinedState):
    summary = state.get("summary", "")
    if summary:
        system_message = f"Summary of conversation earlier: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = state["messages"]
    
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue_or_tools(state: CombinedState) -> Literal["summarize_conversation", "tools", END]:
    messages = state["messages"]
    last_message = messages[-1]
   
    if len(messages) > 6:
        return "summarize_conversation"
    if last_message.tool_calls:
        return "tools"
    return END

def summarize_conversation(state: CombinedState):
    summary = state.get("summary", "")
    summary_message = (
        f"This is summary of the conversation to date: {summary}\n\n"
        "Extend the summary based on new messages:" if summary 
        else "Create a summary of the conversation above:"
    )
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}

def tool_node(state: CombinedState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(CombinedState)

# Define nodes
workflow.add_node("conversation", handle_conversation)
workflow.add_node("summarize_conversation", summarize_conversation)
workflow.add_node("tools", tool_node)

# Set initial node and define transitions
workflow.add_edge(START, "conversation")
workflow.add_conditional_edges("conversation", should_continue_or_tools, ["summarize_conversation", "tools", END])
workflow.add_edge("summarize_conversation", END)
workflow.add_edge("tools", "conversation")

# Compile the application
app = workflow.compile(checkpointer=memory)

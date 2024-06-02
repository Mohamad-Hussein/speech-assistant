from typing import Union, List, Annotated, Sequence, TypedDict, Literal, Optional
import json

from langchain.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder

from langgraph.graph import END, Graph, StateGraph, MessageGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    FunctionMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.tools import tool, BaseTool
from langchain_core.output_parsers.string import StrOutputParser

from langchain_community.llms import Ollama
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import ShellTool

from langchain_experimental.llms.ollama_functions import OllamaFunctions

import chainlit as cl
from src.assistant.tools import (
    prompt_chatqa,
    tools,
    tool_executor,
    MODEL_FUNC,
    MODEL,
    MODEL_DECIDER,
)
from src.assistant.decision_function import DecisionMaker

ollama_model = "llama3-chatqa:8b"
# ollama_model = "llama3:8b"

model = Ollama(model=ollama_model)


def add_messages(left: list, right: list):
    """Add-don't-overwrite."""
    return left + right


def clear_state_messages(messages: list[BaseMessage]):
    """Removes the messages from the nodes in the graph"""

    for val in messages.copy()[::-1]:
        if isinstance(val, AIMessage):
            messages.pop()
        elif isinstance(val, HumanMessage):
            break

    return messages


class AgentState(TypedDict):
    # The `add_messages` function within the annotation defines
    # *how* updates should be merged into the state.
    messages: Annotated[list, add_messages]


def should_continue(
    state: AgentState,
) -> Literal["tool-agent", "tools", "default-agent"]:
    messages = state["messages"]
    last_message = messages[-1]
    # Redo the call if the last message was not a function call
    if "function_call" not in last_message.additional_kwargs:
        return "default-agent"
        # return "tool-agent"
    # If the LLM makes a tool call, then we route to the "tools" node
    return "tools"


def decide(state: AgentState) -> Literal["default-agent", "tool-agent"]:
    messages = state["messages"]
    last_message = messages[-1]
    function_call = last_message.additional_kwargs["function_call"]["name"]

    if "no_system_tool" in function_call:
        return "default-agent"
    elif "use_system_tool" in function_call:
        return "tool-agent"
    else:
        print(f"No correct response")
        return "default-agent"


def call_decider(state: AgentState):
    last_message = state["messages"][-1]
    print(f"This is the decider messages {last_message}")
    response = MODEL_DECIDER.invoke([last_message])

    return {"messages": [response]}


def call_model(state: AgentState):
    messages = state["messages"]
    response = MODEL.invoke(messages)
    return {"messages": [response]}


def call_default_agent(state: AgentState):
    """This is to call the LM for a normal response"""
    messages = state["messages"]
    messages = clear_state_messages(messages)

    print(f"-----\nThese are the messages it is receiving: {messages}")
    response = MODEL.invoke(messages)
    return {"messages": [response]}


# Define the function that calls the model
# @cl.step(name="call_model")
def call_func_model(state: AgentState):
    messages = state["messages"]
    last_message = [messages[-1]]
    response = MODEL_FUNC.invoke(last_message)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


# Define the function to execute tools
def call_tool(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    # Get the tool name and arguments
    tool_called = last_message.additional_kwargs["function_call"]["name"]
    tool_input = last_message.additional_kwargs["function_call"]["arguments"]

    # Making sure json is loaded even if the tool input is empty
    if tool_input != "":
        tool_input = json.loads(tool_input)
    if tool_called == "no_system_tool":
        return {"messages": "No tools called"}

    action = ToolInvocation(
        tool=tool_called,
        tool_input=tool_input,
    )
    # We call the tool_executor and get back a response
    response = tool_executor.invoke(action)
    # We use the response to create a FunctionMessage
    func_message = FunctionMessage(
        content=f"TOOL USED ({action.tool}), RESULT: " + str(response), name=action.tool
    ).dict()

    func_message = f"Tool {action.tool} is used, and here is the result: {response}"

    function_message = SystemMessage(content=str(func_message))
    # We return a list, because this will get added to the existing list
    return {"messages": [func_message]}


def call_summarizer(state: AgentState):
    """This function is called when the user asks for a summary of the results of the tool."""
    last_message = state["messages"][-1]

    model = Ollama(model="llama3-chatqa:8b")

    prompt_chatqa = PromptTemplate.from_template(
        """System: You are a smart assistant that summarizes the results of tools used by an agent.
        You will be given the name of the tool used as well as the output of that tool.
        Notify the user in a natural manner and keep it concise.


        {instructions}

        {result}

        Assistant:"""
    )
    response = model.invoke(last_message)

    return {"messages": [response]}

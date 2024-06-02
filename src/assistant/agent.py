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
)
from langchain_core.tools import tool, BaseTool
from langchain_core.output_parsers.string import StrOutputParser

from langchain_community.llms import Ollama
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import ShellTool

from langchain_experimental.llms.ollama_functions import OllamaFunctions

import chainlit as cl
from src.assistant.tools import prompt_chatqa, tools, tool_executor, MODEL_FUNC, MODEL
from src.assistant.graph import (
    AgentState,
    call_decider,
    call_func_model,
    call_tool,
    call_default_agent,
    decide,
    should_continue,
)


# initialize the graph
def create_graph():
    """Returns a graph that contains the nodes and edges for the conversational system."""

    graph = StateGraph(AgentState)

    graph.add_node("decision-maker", call_decider)
    graph.add_node("tool-agent", call_func_model)
    graph.add_node("tools", call_tool)
    graph.add_node("default-agent", call_default_agent)

    graph.add_conditional_edges(
        "decision-maker",
        decide,
        path_map={
            "default-agent": "default-agent",
            "tool-agent": "tool-agent",
        },
    )
    graph.add_conditional_edges(
        "tool-agent",
        should_continue,
        {
            "tools": "tools",
            "tool-agent": "tool-agent",
        },
    )
    # graph.add_edge("tools", "agent")
    graph.add_edge("tools", END)
    graph.add_edge("default-agent", END)

    graph.set_entry_point("decision-maker")

    runnable = graph.compile()
    print(runnable.get_graph().print_ascii())

    chain = runnable
    return chain


# for output in runnable.stream(inputs, stream_mode="updates"):
#     # stream() yields dictionaries with output keyed by node name
#     for key, value in output.items():
#         print(f"Output from node '{key}':")
#         print("---")
#         print(value)
#     print("\n---\n")


def create_agent(llm, system_message: Optional[str] = None):

    # # initialize conversational memory
    # conversational_memory = ConversationBufferWindowMemory(
    #     memory_key="messages", k=5, return_messages=True,
    # )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                "You are a helpful AI assistant, helping the user accomplish their task."
                "Messages: \n\n{history}\n\n",
            ),
            ("user", "{user_input}"),
        ]
    )

    prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

    chain = prompt | llm | StrOutputParser()
    chain.name = llm.model

    return chain

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

from langchain_community.chat_models import ChatOllama
from langchain_community.llms import Ollama
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import ShellTool

from langchain_experimental.llms.ollama_functions import OllamaFunctions

import chainlit as cl
from src.assistant.tools import tools, build_models, LLM_SYSTEM_PROMPT
from src.assistant.graph import (
    AgentState,
    AgentGraph,
    call_tool,
    decide,
    should_continue,
)


# initialize the graph
def create_graph(
    model: str, base_url: Optional[str] = "http://localhost:11434"
):
    """Returns a graph that contains the nodes and edges for the conversational system."""

    # NOTE Did it this way to persist the models in the Chainlit context
    default_model, model_decider, model_func = build_models(model, ollama_url=base_url)
    models = AgentGraph(
        ollama_model=model,
        default_model=default_model,
        model_decider=model_decider,
        model_func=model_func,
    )

    graph = StateGraph(AgentState)

    graph.add_node("decision-maker", models.call_decider)
    graph.add_node("tool-agent", models.call_func_model)
    graph.add_node("tools", call_tool)
    graph.add_node("default-agent", models.call_default_agent)

    # Deciding between calling system tools or respond with default agent
    graph.add_conditional_edges(
        "decision-maker",
        decide,
        path_map={
            "default-agent": "default-agent",
            "tool-agent": "tool-agent",
        },
    )

    # Choice of either calling system tools or regenerate tool call
    graph.add_conditional_edges(
        "tool-agent",
        should_continue,
        {
            "tools": "tools",
            "tool-agent": "tool-agent",
        },
    )

    graph.add_edge("tools", END)
    graph.add_edge("default-agent", END)
    graph.set_entry_point("decision-maker")

    runnable = graph.compile()
    print(runnable.get_graph().print_ascii())

    chain = runnable

    # Changing name
    chain.name = model + " agent" if model != "None" else "None"
    return chain


def create_agent(model: str, base_url: str, system_message: Optional[str] = None):

    llm = ChatOllama(model=model, base_url=base_url)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                # "You are a helpful AI assistant, helping the user accomplish their task."
                LLM_SYSTEM_PROMPT
            ),
            MessagesPlaceholder(variable_name="history"),
        ]
    )

    prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

    chain = prompt | llm | StrOutputParser()
    chain.name = llm.model

    return chain

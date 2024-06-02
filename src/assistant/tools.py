from typing import Union, List, Annotated, Sequence, TypedDict, Literal, Optional
import json
import subprocess
import operator
import datetime

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool, Tool, tool
from langchain.tools.render import format_tool_to_openai_function
from langchain.chains.conversation.memory import ConversationBufferWindowMemory

from langgraph.graph import END, Graph, StateGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langgraph.graph import END, MessageGraph

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import (
    ToolMessage,
    HumanMessage,
    BaseMessage,
    FunctionMessage,
)
from langchain_core.tools import tool, BaseTool
from langchain_core.utils.function_calling import convert_to_openai_function

from langchain_community.llms import Ollama
from langchain_experimental.llms.ollama_functions import (
    OllamaFunctions,
    convert_to_ollama_tool,
)

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import ShellTool

from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain_core.messages import HumanMessage
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool, Tool, tool
from src.assistant.decision_function import DecisionMaker
import langchain
langchain.debug = True

from langchain.callbacks.base import BaseCallbackHandler

# ollama_model = "llama3-chatqa:8b"
ollama_model = "llama3:8b"

MODEL = Ollama(model=ollama_model)
MODEL_FUNC = OllamaFunctions(model=ollama_model, format="json")
MODEL_DECIDER = OllamaFunctions(model=ollama_model, format="json")

# Setting the decider calling prompt
MODEL_DECIDER.tool_system_prompt_template = """You have access to the following tools:

{tools}

You must always select one of the above tools and respond with only a JSON object matching the following schema:

{{
  "tool": <name of the selected tool>,
  "tool_input": <parameters for the selected tool, matching the tool's JSON schema>
}}
"""
# Setting the function calling prompt
MODEL_FUNC.tool_system_prompt_template = """You are a smart assistant that helps the user find the information he is looking for using tools. 

You have access to the following tools:

{tools}


You must always select one of the above tools and respond with only a JSON object matching the following schema:

{{
  "tool": <name of the selected tool>,
  "tool_input": <parameters for the selected tool, matching the tool's JSON schema>
}}

If provided tools does not satisfy the user request, then on tools should be used and use the following JSON object as your response.

{{
  "tool": no_system_tool
  "tool_input": {{}}
}}
"""

@tool
def multiply_calculator(
    number1: Union[int, float], number2: Union[int, float]
) -> Union[int, float]:
    """A tool that multiplies two numbers together"""
    return number1 * number2


@tool
def get_time(location: Optional[str] = None) -> str:
    """A tool that returns the current date and time in the form of %B %d, %Y %I:%M %p"""
    return datetime.datetime.now().strftime("%B %d, %Y %-I:%M %p")

@tool
def inform_user(text: str) -> None:
    """Prints the text"""
    print(text)

# Tool dictionaries
tool_multiply_dict = {
    "name": multiply_calculator.name,
    "description": multiply_calculator.description,
    "parameters": {
        "type": "object",
        "properties": {
            "number1": {"type": ["integer", "number"]},
            "number2": {"type": ["integer", "number"]},
        },
        "required": ["number1", "number2"],
    },
}
tool_time_dict = {
    "name": get_time.name,
    "description": get_time.description,
    "parameters": {
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": [],
    },
}

DEFAULT_RESPONSE_FUNCTION = {
    "name": "response",
    "description": (
        "Respond conversationally if no other tools should be called for a given query. ",
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "response": {
                "type": "string",
                "description": "Conversational response to the user.",
            },
        },
        "required": ["response"],
    },
}

MODEL_FUNC = MODEL_FUNC.bind_tools(
    tools=[
        tool_time_dict,
        tool_multiply_dict,
        # DEFAULT_RESPONSE_FUNCTION,
    ],
)

# Tools
tools = [
    multiply_calculator,
    get_time,
]
# Initialize the tool executor
tool_executor = ToolExecutor(tools=tools)

# Prompt template llama3
prompt_chatqa = PromptTemplate.from_template(
    """System: You are a part of a group of assistant agents that accomplishes requests
    from the user. The agents are trained to understand user requests and respond in a
    natural language manner. Tools can be used by the user to interact with his computer.
    Notify the user of the results of the tools that are used.

    {history}
    
    User: {user_input}

    Assistant:"""
)

MODEL_DECIDER = DecisionMaker(model=ollama_model, format="json")

@tool
def no_system_tool():
    """Call this when no system tool is needed to answer the user"""
    return "No tool was used."


@tool
def use_system_tool():
    """Call this when tool is needed to get an output from the user's computer system"""
    return "Tool should be used."


no_tools = convert_to_openai_function(no_system_tool)
use_tools = convert_to_openai_function(use_system_tool)

decision_tools = [no_tools, use_tools]

# Setting the prompt template for the model
tool_format = json.dumps(
    [
        tool_time_dict,
        tool_multiply_dict,
    ],
    indent=2,
)
prompt_template = """
System: You are a smart assistant that is in charge of deciding if the user is asking
an assistant to use a system tool on his computer.

The assistant has access to the following system tools:

Getting time from the user's system, and multiplying two numbers.

You have access to the following decision tools:

{tools}

Only select with a decision tool!
You must always select one of the above decision tools for your decision and respond with only a JSON object matching the following schema:

{{
  "tool": <name of the decision tool>,
}}

If you are not sure which tool to use, choose no_system_tool.
"""
# [\n{\n"name": "no_system_tool",\n    "description": "Call this when no system tool is needed to answer the user",\n    "parameters": {\n      "type": "object",\n      "properties": {\n        "request": {}\n      },\n      "required": [\n        "request"\n      ]\n    }\n  },\n  {\n    "name": "use_system_tool",\n    "description": "Call this when tool is needed to get an output from the user\'s computer system",\n    "parameters": {\n      "type": "object",\n      "properties": {\n        "request": {}\n      },\n      "required": [\n        "request"\n      ]\n    }\n  }\n]


MODEL_DECIDER.tool_system_prompt_template = prompt_template
MODEL_DECIDER = MODEL_DECIDER.bind_tools(tools=decision_tools)

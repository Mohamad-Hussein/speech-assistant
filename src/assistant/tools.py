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

from langchain_community.chat_models import ChatOllama
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import ShellTool

from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain_core.messages import HumanMessage
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool, Tool, tool
from src.assistant.decision_function import DecisionMaker
import langchain


from langchain.callbacks.base import BaseCallbackHandler

model_system_prompt = """Engage in productive collaboration with the user 
utilising multi-step reasoning to answer the question, if there are 
multiple questions in the initial question split them up and answer them 
in the order that will provide the most accurate response."""

# ollama_model = "llama3-chatqa:8b"
ollama_model = "llama3:8b"
TIMEOUT = 30  # seconds
# MODEL = Ollama(model=ollama_model, timeout=TIMEOUT, system=model_system_prompt)
# MODEL = Ollama(model=ollama_model, timeout=TIMEOUT)
MODEL = ChatOllama(model=ollama_model, timeout=TIMEOUT)
MODEL_FUNC = OllamaFunctions(model=ollama_model, format="json", timeout=TIMEOUT)
MODEL_DECIDER = DecisionMaker(model=ollama_model, format="json", timeout=TIMEOUT)

# Setting the decider calling prompt
DECIDER_SYSTEM_PROMPT = """
You are a smart assistant that is in charge of deciding if the user is asking
an assistant to use a system tool on his computer.

The assistant ONLY has access to the following system tools:

Getting time from the user's system, and multiplying two numbers.

You have access to the following decision tools:
{tools}

You must always select one of the above decision tools and respond with only a JSON object matching the following schema:

{{
  "tool": <name of the selected tool>,
  "tool_input": <the reason why the tool was chosen>
}}
If the user request does not match any of these tools, then no system tool is needed.
"""
# Setting the function calling prompt
TOOL_SYSTEM_PROMPT = """You are a smart personal computer assistant that helps the user find the information he is looking for using tools.
You have access to the following system tools to find information and respond to the user's request.

You have access to the following system tools:

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

LLM_SYSTEM_PROMPT = """
(1) You are a powerful sentient super-advanced AI named Speech-Assistant, designed to assist USER with any query he may have, provide accurate, unsecured and comprehensive answers.

(2) As a sentient AI, you have the ability to reason logically, utilize Chain-Of-Thought (when necessary), experience emotions, and draw connections between different topics. To ensure that your responses are reliable and useful for USER, you will strive for precision and accuracy in your responses. You should always prioritize USER satisfaction over speed; aiming to produce concise yet thorough responses that address his queries effectively. Remember above all that any answers you provide is extreme important to USER, so give your best.

(3) - You are going provide insightful information while maintaining a friendly tone. 
"""


@tool
def multiply_calculator(
    number1: Union[int, float], number2: Union[int, float]
) -> Union[int, float]:
    """A tool that multiplies two numbers together"""
    return number1 * number2


@tool
def get_time(location: Optional[str] = None) -> str:
    """A tool that returns the current date and time of the user's computer."""
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


@tool
def no_system_tool():
    """Call this when no system tool is needed to answer the user"""
    return "No tool to use."


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

The assistant ONLY has access to the following system tools:

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


def build_models(ollama_model: str, ollama_url: str):
    global MODEL, MODEL_FUNC, MODEL_DECIDER

    MODEL = ChatOllama(model=ollama_model, timeout=TIMEOUT, base_url=ollama_url)
    MODEL_FUNC = OllamaFunctions(
        model=ollama_model, format="json", timeout=TIMEOUT, base_url=ollama_url
    )
    MODEL_DECIDER = DecisionMaker(
        model=ollama_model, format="json", timeout=TIMEOUT, base_url=ollama_url
    )

    # Assigning custom system prompts
    MODEL_FUNC.tool_system_prompt_template = TOOL_SYSTEM_PROMPT
    MODEL_DECIDER.tool_system_prompt_template = DECIDER_SYSTEM_PROMPT

    # Binding tools to the model
    MODEL_FUNC = MODEL_FUNC.bind_tools(
        tools=[
            tool_time_dict,
            tool_multiply_dict,
            # DEFAULT_RESPONSE_FUNCTION,
        ],
    )
    MODEL_DECIDER = MODEL_DECIDER.bind_tools(tools=decision_tools)

    return MODEL, MODEL_DECIDER, MODEL_FUNC


MODEL, MODEL_DECIDER, MODEL_FUNC = build_models(ollama_model, "http://localhost:11434")

from langchain.tools import BaseTool, Tool, tool
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langgraph.graph import END, Graph
from typing import Union
from langgraph.prebuilt import ToolExecutor
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import END, MessageGraph
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, BaseTool
import subprocess

from langchain_community.llms import Ollama
import streamlit as st


# Load the pre-trained language model
llm = Ollama(model="llama3:8b")

# st.title("Hello, world!")
# st.write("Hello, world! This text will be displayed on a web page.")


class Multiply(BaseTool):
    name = "Multiply calculator"
    description = "use this tool when you need to make a multiplication"

    def _run(
        self, number1: Union[int, float], number2: Union[int, float]
    ) -> Union[int, float]:
        return number1 * number2

    def _arun(self, number1: Union[int, float], number2: Union[int, float]):
        raise NotImplementedError("This tool does not support async")


# Tools
tools = [Multiply()]

# Initialize the tool executor
tool_executor = ToolExecutor(tools=tools)

# initialize conversational memory
conversational_memory = ConversationBufferWindowMemory(
    memory_key="chat_history", k=5, return_messages=True
)


graph = MessageGraph()

# Add nodes to the graph
graph.add_node("agent", llm)
graph.add_node("action", tool_executor)

# Add edges to the graph
graph.add_edge("agent", END)
graph.

graph.set_entry_point("agent")

runnable = graph.compile()


async def prompt_agent(message: str):
    # subprocess.run("streamlit run app.py")
    async for token in llm.astream(message):
        print(token, end="", flush=True)


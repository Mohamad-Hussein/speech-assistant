import subprocess
from typing import Union, Optional

from langchain.chains import LLMChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool, Tool, tool
from langchain.schema import StrOutputParser
from langchain.schema.runnable.config import RunnableConfig

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import ToolMessage, HumanMessage
from langchain_core.tools import tool, BaseTool

from langgraph.graph import END, Graph, MessageGraph
from langgraph.prebuilt import ToolExecutor

from langchain_community.llms import Ollama


class Multiply(BaseTool):
    name = "Multiply calculator"
    description = "use this tool when you need to make a multiplication"

    def _run(
        self, number1: Union[int, float], number2: Union[int, float]
    ) -> Union[int, float]:
        return number1 * number2

    def _arun(self, number1: Union[int, float], number2: Union[int, float]):
        raise NotImplementedError("This tool does not support async")


tools = [Multiply()]
tool_executor = ToolExecutor(tools=tools)


def create_agent(llm, system_message: Optional[str] = None):

    # # initialize conversational memory
    # conversational_memory = ConversationBufferWindowMemory(
    #     memory_key="messages", k=5, return_messages=True, 
    # )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful AI assistant, helping the user accomplish their task."
                " Use the provided tools to progress towards answering the question."
                " You have access to the following tools: {tool_names}.\n\n"
                "Messages: \n\n{history}\n\n"
            ),
            # MessagesPlaceholder(variable_name="messages"),
            # ("system", "{history}"),
            ("user", "{user_input}"),
        ]
    )
    prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

    chain = prompt | llm | StrOutputParser()
    chain.name = llm.model
    
    return chain
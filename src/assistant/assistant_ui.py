import os
import sys

sys.path.append(os.getcwd())

from fastapi import Request, Response
from fastapi.responses import (
    HTMLResponse,
)
import logging
import logging.config

import chainlit as cl
from chainlit.input_widget import Select
from chainlit.server import app
from chainlit.context import init_http_context, init_ws_context
from chainlit.session import WebsocketSession, ws_sessions_id
import langchain

langchain.verbose = True
from langchain_core.messages import (
    ToolMessage,
    HumanMessage,
    BaseMessage,
    FunctionMessage,
    AIMessage,
)
from langchain.schema.runnable.config import RunnableConfig
from langchain_community.llms import Ollama

from src.assistant.agent import create_agent, create_graph
from src.config import DEFAULT_AGENT, AGENT_MODELS, OLLAMA_HOST
from src.config import get_from_config

AGENT_TOOLS_ENABLED: bool = True


async def inference(message: str):
    """
    Inference function when the assistant is started
    """
    # Getting the agent
    agent = cl.user_session.get("agent")
    if agent.name == "None":
        await cl.Message(
            f"No agent is selected. Please select an agent in the options tab in the GUI.",
            author="System",
        ).send()
        return

    history: list[BaseMessage] = cl.user_session.get("history")

    user_message = message if isinstance(message, str) else message.content
    cb = cl.AsyncLangchainCallbackHandler(stream_final_answer=True)
    # inputs = {"messages": [history_log + user_message]}
    history.append(HumanMessage(user_message, role="User"))
    inputs = {"messages": history}

    if AGENT_TOOLS_ENABLED:
        for output in agent.stream(
            inputs,
            stream_mode="updates",
            config=RunnableConfig(callbacks=[cb]),
        ):
            # stream() yields dictionaries with output keyed by node name
            for key, value in output.items():
                print(f"Output from node '{key}':")
                print("---")
                print(value)

            print("\n---\n")

        ai_message = value["messages"][0]
        # Remove "AI:" and strip any leading whitespace
        if ai_message.startswith("AI:"):
            ai_message = ai_message[len("AI:") :].lstrip()

        await cl.Message(content=ai_message).send()
    else:
        msg = cl.Message(content="", author=agent.name)
        async for token in agent.astream(
            {"history": history, "user_input": message.content},
        ):
            await msg.stream_token(token)

        ai_message = msg.content

    # Saving history
    history.append(AIMessage(ai_message, role="Assistant"))
    # history.append({"User": user_message})
    # history.append({"Assistant": ai_message})
    print("History:", history)

    return ai_message


@cl.on_chat_start
async def start():
    """This is done everytime a new sessions starts"""

    session_id = cl.user_session.get("id")

    # Logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=os.path.join("logs", "llm-ui.log"),
        filemode="w",
    )
    logger = logging.getLogger(__name__)

    # Create the agent
    model = get_from_config("Default Agent Model")
    if AGENT_TOOLS_ENABLED:
        agent = create_graph()
    else:
        llm = Ollama(model=model, base_url=OLLAMA_HOST)
        agent = create_agent(llm)

    logger.info(f"Starting new session with id {session_id}, using llm {model}")

    # Store the agent in session
    cl.user_session.set("agent", agent)
    cl.user_session.set("user", "User")
    cl.user_session.set("history", [])

    await cl.Avatar(
        name="You",
        path="icons/user-icon.png",
    ).send()

    # UI elements
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="Agent Model",
                values=AGENT_MODELS,
                # initial_index=AGENT_MODELS.index(model),
                initial_index=1,
                description="Select the agent model you want to use.",
            )
        ]
    ).send()

    print(cl.User("User").identifier)
    print("Session id: ", cl.user_session.get("id"))
    print("Environment: ", cl.user_session.get("env"))
    print("Chat settings: ", cl.user_session.get("chat_settings"))
    print("User: ", cl.user_session.get("user"))
    print("Chat profile: ", cl.user_session.get("chat_profile"))
    print("Languages: ", cl.user_session.get("languages"))
    print("SESSION_ID: ", session_id)

    await cl.Message(f"Hello! How can I help you?", author=agent.name).send()


@cl.author_rename
def rename(orig_author: str):
    # rename_dict = {"You": "User"}
    rename_dict = {}
    return rename_dict.get(orig_author, orig_author)


@cl.on_settings_update
async def setup_agent(settings):
    """This is to update the agent model through web ui"""
    print("on_settings_update", settings)

    # Updating the agent
    model = settings["Model"]
    agent = create_graph()
    # llm = Ollama(model=model, base_url=OLLAMA_HOST)
    # agent = create_agent(llm)
    cl.user_session.set("agent", agent)


@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="Agent Inference",
            markdown_description="For llm inference",
            icon="https://picsum.photos/200",
        ),
        # cl.ChatProfile(
        #     name="Agent Actions",
        #     markdown_description="Agent actions",
        #     icon="https://picsum.photos/200",
        # ),
    ]


@cl.on_message
async def on_message(message: cl.Message):
    """This is when user types his message on the ui and sends it."""

    async with cl.Step() as step:
        await inference(message)

    # input = {"user_input": message.content}
    # res = await agent.arun(user_input=input, callbacks=[cl.LangchainCallbackHandler()])


@cl.on_logout
def logout(request: Request, response: Response):
    response.delete_cookie("my_cookie")


@app.get("/id")
async def id(
    request: Request,
):
    """This is to get the id of the latest Websocket context used
    by the user"""
    init_http_context()

    ## This is a way to get a new id, not for websocket
    # from chainlit.context import context

    # context.session.languages = ["en-US"]
    # id = cl.user_session.get("id")

    print(f"\nCurrent sessions: {ws_sessions_id}\n")

    curr_session_id = list(ws_sessions_id.keys())[-1]
    print(f"Current session id: {curr_session_id}")

    return {"id": curr_session_id}


## Websocket endpoints for sending messages and posting user messages ##
@app.post("/user/{session_id}")
async def update_user_message(
    request: Request,
    session_id: str,
):
    """This is to update user message when transcription request is complete."""
    session_id = list(ws_sessions_id.keys())[-1]

    ws_session = WebsocketSession.get_by_id(session_id=session_id)
    init_ws_context(ws_session)

    data = await request.json()
    user_input = data.get("message")
    print("Received message from user:", user_input)

    res = await cl.Message(content=user_input, author="You").send()

    return {
        "status": 200,
        "user message": user_input,
        "session_id": session_id,
    }


@app.post("/model/{model}/{session_id}")
async def update_agent(
    request: Request,
    model: str,
    session_id: str,
):
    """This is to change the agent model to the user request"""
    # Getting the last session
    session_id = list(ws_sessions_id.keys())[-1]
    ws_session = WebsocketSession.get_by_id(session_id=session_id)
    init_ws_context(ws_session)

    # Updating the agent
    agent = create_graph()
    # llm = Ollama(model=model, base_url=OLLAMA_HOST)
    # agent = create_agent(llm)

    cl.user_session.set("agent", agent)

    # Give response to the user
    await cl.Message(f"Agent {model} is selected", author="System").send()

    return {
        "status": 200,
        "model": f"Agent model set to {model}",
        "session_id": session_id,
    }


@app.post("/message/{session_id}")
async def receive_message(request: Request, session_id: str):
    """This is for llm inference once the transcription pipeline request is complete"""
    # Getting the websocket session
    session_id = list(ws_sessions_id.keys())[-1]
    ws_session = WebsocketSession.get_by_id(session_id=session_id)
    init_ws_context(ws_session)
    print("Websocket session id:", session_id)

    # Getting the message from ASR backend
    data = await request.json()
    message = data.get("message")
    print("Received message: ", message)

    msg = cl.Message(content="")
    await msg.send()

    await inference(message)

    return {
        "status": 200,
        # "response": "".join(llm_response),
        "session_id": session_id,
    }


def format_history(history):
    history_log = ""
    for transaction in history:
        key, val = next(iter(transaction.items()))
        history_log += f"{key}: {val}\n\n"
    return history_log


def run_app():

    from chainlit.cli import run_chainlit

    run_chainlit(__file__)


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)

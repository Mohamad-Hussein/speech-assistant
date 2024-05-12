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
from chainlit.server import app
from chainlit.context import init_http_context, init_ws_context
from chainlit.session import WebsocketSession, ws_sessions_id

from langchain.schema.runnable.config import RunnableConfig
from langchain_community.llms import Ollama

from src.assistant.assistant import create_agent
from src.config import DEFAULT_AGENT, get_from_config


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
    agent_model = get_from_config("Default Agent Model")
    llm = Ollama(model=agent_model)
    agent = create_agent(llm)

    logger.info(f"Starting new session with id {session_id}, using llm {agent_model}")

    # Store the agent in session
    cl.user_session.set("agent", agent)
    cl.user_session.set("user", cl.User("User"))
    cl.user_session.set("history", [])

    print(cl.User("User").identifier)

    print("Session id: ", cl.user_session.get("id"))
    print("Environment: ", cl.user_session.get("env"))
    print("Chat settings: ", cl.user_session.get("chat_settings"))
    print("User: ", cl.user_session.get("user"))
    print("Chat profile: ", cl.user_session.get("chat_profile"))
    print("Languages: ", cl.user_session.get("languages"))
    print("SESSION_ID: ", session_id)

    app_user = cl.user_session.get("user")
    await cl.Message(f"Hello {app_user}. How can I help you?", author=agent.name).send()
    # cl.Avatar(name="User")
    # cl.Avatar(name="llama3:8b")


@cl.author_rename
def rename(orig_author: str):
    rename_dict = {"You": "User"}
    return rename_dict.get(orig_author, orig_author)


@cl.on_message
async def message(message: cl.Message):
    """This is when user types his message on the ui and sends it."""
    # Getting the agent
    agent = cl.user_session.get("agent")
    history = cl.user_session.get("history")
    # llm.
    # Formatting history
    history_log = format_history(history)

    print("History:\n", history_log)

    # Writing agent message
    msg = cl.Message(content="", author=agent.name)

    await msg.send()

    # tokens = []
    # async for token in agent.astream(message.content):
    #     # await msg.stream_token(token)
    #     tokens.append(token)
    # print(tokens)

    async for chunk in agent.astream(
        {"history": history_log, "user_input": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)

    await msg.send()

    # Saving history
    history.append({"Human": message.content})
    history.append({"AI": msg.content})
    print("History:", history)

    # input = {"user_input": message.content}
    # res = await agent.arun(user_input=input, callbacks=[cl.LangchainCallbackHandler()])


@cl.on_logout
def main(request: Request, response: Response):
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

    res = await cl.Message(content=user_input, author="User").send()

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
    llm = Ollama(model=model)
    agent = create_agent(llm)
    cl.user_session.set("agent", agent)

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

    # Getting the agent
    agent = cl.user_session.get("agent")
    history = cl.user_session.get("history")

    # Formatting history
    history_log = format_history(history)

    # Process the incoming message
    msg = cl.Message(content="", author=agent.name)
    await msg.send()

    llm_response = []
    async for chunk in agent.astream(
        {"history": history_log, "user_input": message},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        llm_response.append(chunk)
        await msg.stream_token(chunk)

    await msg.send()

    # Saving history
    history.append({"Human": message})
    history.append({"AI": msg.content})

    return {
        "status": 200,
        "response": "".join(llm_response),
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
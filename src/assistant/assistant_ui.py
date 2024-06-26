import os
import sys
from typing import Union, Optional
import logging
import logging.config
from multiprocessing.queues import Queue as QueueType
from multiprocessing import Queue


sys.path.append(os.getcwd())

from fastapi import Request, Response


import chainlit as cl
from chainlit.input_widget import Select, Switch, TextInput
from chainlit.server import app
from chainlit.context import init_http_context, init_ws_context
from chainlit.session import WebsocketSession, ws_sessions_id

from langchain_core.messages import (
    ToolMessage,
    HumanMessage,
    BaseMessage,
    FunctionMessage,
    AIMessage,
)
from langchain.schema.runnable.config import RunnableConfig
from langchain_community.llms import Ollama
from langchain_community.chat_models.ollama import ChatOllama

from src.assistant.agent import create_agent, create_graph
from src.config import (
    get_from_config,
    update_config,
    DEFAULT_AGENT,
    AGENT_MODELS,
    OLLAMA_HOST,
    CHAINLIT_HOST,
    CHAINLIT_PORT,
)

from PIL import Image
from io import BytesIO
import base64

# langchain.verbose = True
# langchain.debug = True


async def transcribe_audio(audio: list):

    # from chainlit import secret
    from chainlit import secret

    # Send error if no audio queue is available
    if not type(secret.chars) == QueueType:
        await cl.ErrorMessage(
            "There is no queue to send the audio to the Speech-Assistant ASR module",
            author="Error",
        ).send()

    # Multiple files
    res = None
    if len(audio) > 1:
        res = await cl.AskActionMessage(
            content="Would you like to transcribe multiple audio files?",
            author="Speech-Assistant",
            actions=[
                cl.Action(name="continue", value="continue", label="✅ Continue"),
                cl.Action(name="cancel", value="cancel", label="❌ Cancel"),
            ],
        ).send()
    # Return on cancel
    if res and res.get("value") == "cancel":
        return

    # Iterating over the audio files
    for file in audio:

        # Sending sound to model for inference
        queue: Queue = secret.chars
        queue.put({"message": file.path, "do_action": False})

        output = queue.get(block=True, timeout=10)
        transcription = output.get("transcription", None)

        if transcription:
            # This to keep queue in the global scope
            print(f"\n\nResults: {transcription}\n\n")
            await cl.Message(
                f"**Transcription of `{file.name}`:** \n\n{transcription}",
                author="Speech-Assistant",
            ).send()
        else:
            await cl.ErrorMessage(
                f"Please start the transcription service on the GUI and try again.",
                author="❌ Error",
            ).send()
            return

    await cl.Message(f"**Transcription Finished!**", author="Speech-Assistant").send()


async def inference_with_image(message: cl.Message, images: list):

    history = cl.user_session.get("history")
    history.append(HumanMessage(message.content + "\n[Image]\n"))

    vision_model = cl.user_session.get("vision model")

    # Read the first image
    with Image.open(images[0].path) as img:
        with BytesIO() as buffer:
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

    model = Ollama(
        model=vision_model,
    )
    model = model.bind(images=[img_str])
    input = [HumanMessage(content=message.content)]

    # Inference
    msg = cl.Message(content="", author=vision_model)
    async for token in model.astream(input):
        await msg.stream_token(token)

    # Update the history
    history.append(AIMessage(msg.content))


async def inference(message: str):
    """
    Inference function when the assistant is started
    """
    # Getting the agent
    settings = cl.user_session.get("chat_settings")
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
    history.append(HumanMessage(user_message))

    inputs = {"messages": history}

    if settings["Tools Enabled"]:
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
        if isinstance(ai_message, BaseMessage):
            ai_message = ai_message.content

        # Remove "AI:" and strip any leading whitespace
        if ai_message.startswith("AI:"):
            ai_message = ai_message[len("AI:") :].lstrip()

        await cl.Message(content=ai_message, author=agent.name).send()
    else:
        msg = cl.Message(content="", author=agent.name)
        async for token in agent.astream(
            {"history": history},
        ):
            await msg.stream_token(token)

        ai_message = msg.content

    # Saving history
    history.append(AIMessage(ai_message))

    return ai_message


@cl.on_chat_start
async def start():
    """This is done everytime a new sessions starts"""

    # Logging
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=os.path.join("logs", "llm-ui.log"),
        filemode="w",
    )
    logger = logging.getLogger(__name__)

    from chainlit import secret

    if type(secret.chars) == QueueType:
        # This to keep queue in the global scope
        queue: Queue = secret.chars
        logger.debug(f"\nQueue to ASR process included: {queue}\n")

    # User avatar icon
    await cl.Avatar(
        name="You",
        path="icons/user-icon.png",
    ).send()

    # Create the agent
    model = get_from_config("Default Agent Model")
    user_model_list: list[str] = get_from_config("User Models List") or []
    vision_model = "llava-llama3"

    # Settings
    settings = await update_settings_ui((AGENT_MODELS + user_model_list).index(model))

    if settings["Tools Enabled"]:
        agent = create_graph(model=model, base_url=OLLAMA_HOST)

    else:
        agent = create_agent(model=model, base_url=OLLAMA_HOST)

    # Store the agent in session
    cl.user_session.set("agent", agent)
    cl.user_session.set("vision model", vision_model)
    cl.user_session.set("user", "User")
    cl.user_session.set("history", [])
    cl.user_session.set("logger", logger)

    logger.info(f"Open chat window...")
    logger.debug(f"User identifier: {cl.User('User').identifier}")
    logger.debug(f"Session id: {cl.user_session.get('id')}")
    logger.debug(f"Environment: {cl.user_session.get('env')}")
    logger.debug(f"Chat settings: {cl.user_session.get('chat_settings')}")
    logger.debug(f"User: {cl.user_session.get('user')}")
    logger.debug(f"Chat profile: {cl.user_session.get('chat_profile')}")
    logger.debug(f"Languages: {cl.user_session.get('languages')}")
    logger.debug(f"SESSION_ID: {cl.user_session.get('id')}")

    await cl.Message(f"Hello! How can I help you?", author=agent.name).send()


@cl.author_rename
def rename(orig_author: str):
    # rename_dict = {"You": "User"}
    rename_dict = {}
    return rename_dict.get(orig_author, orig_author)


@cl.on_settings_update
async def settings_update(settings):
    """This is to update the agent model through web ui"""
    logger = cl.user_session.get("logger")
    logger.info(f"on_settings_update: {settings}")

    # Getting the model
    model = settings["Model"]
    model_list = get_from_config("User Models List")

    # Updating new model
    new_model: Union[str, None] = settings["Add Model"]

    if new_model and new_model.lower().strip() != "":

        new_model = new_model.lower().strip()

        # Make sure that the model is available
        async with cl.Step(
            name=f"Checking if `{new_model}` is installed in Ollama"
        ) as step:
            # Step is sent as soon as the context manager is entered
            await step.stream_token(f"Checking model...")

            # Give an error message
            try:
                model = Ollama(model=new_model, base_url=OLLAMA_HOST)
                model.invoke("")
                await step.stream_token(f" Model `{new_model}` found and loaded!")

            except Exception as e:
                await cl.ErrorMessage(f"{str(e)}", author="Error").send()
                await step.stream_token(f" Model `{new_model}` not found in Ollama.")
                return

        # Save the new model to config file
        model_list = list(set(model_list + [new_model])) if model_list else [new_model]
        update_config("User Models List", model_list)

        # Switching to new model in UI
        settings["Model"] = new_model
        new_model_idx = (AGENT_MODELS + model_list).index(new_model)
        settings = await update_settings_ui(new_model_idx)

        # Overriding the model
        model = new_model

        # Sending message
        await cl.Message("Hello! How can I help you?", author=new_model).send()

    # Saving user defined settings
    update_config("Tools Enabled", settings["Tools Enabled"])
    update_config("Default Agent Model", model)
    # Updating the agent
    if settings["Tools Enabled"]:
        agent = create_graph(model=model, base_url=OLLAMA_HOST)

    else:
        agent = create_agent(model=model, base_url=OLLAMA_HOST)
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

    # Processing images and audio exclusively
    images = [file for file in message.elements if "image" in file.mime]
    audio = [file for file in message.elements if "audio" in file.mime]

    print([file for file in message.elements])
    # Image prompt
    if images:
        await inference_with_image(message, images)

    # Audio files to transcribe
    elif audio:
        await transcribe_audio(audio)

    # Normal prompt
    else:
        async with cl.Step(name="request to LLM response") as step:
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
    # Get the context from the session id
    session_id = list(ws_sessions_id.keys())[-1]
    ws_session = WebsocketSession.get_by_id(session_id=session_id)
    init_ws_context(ws_session)

    # Get the message from the request
    data = await request.json()
    user_input = data.get("message")
    logger = cl.user_session.get("logger")
    logger.info(f"Received message from user: {user_input}")

    # Send the user message to UI
    await cl.Message(content=user_input, author="You").send()

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
    settings = cl.user_session.get("chat_settings")

    # Updating the model in settings tab
    user_model_list = get_from_config("User Models List") or []

    new_model_idx = (AGENT_MODELS + user_model_list).index(model)
    settings = await update_settings_ui(new_model_idx)

    if settings["Tools Enabled"]:
        agent = create_graph(model=model, base_url=OLLAMA_HOST)

    else:
        agent = create_agent(model=model, base_url=OLLAMA_HOST)

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

    logger = cl.user_session.get("logger")
    logger.info(f"Websocket session id: {session_id}")

    try:
        # Getting the message from ASR backend
        data = await request.json()
        message = data.get("message")
        logger.info(f"Received message: {message}")

        # Doing inference
        await inference(message)
    except Exception as e:
        await cl.ErrorMessage(f"Error: {e}", author="Error").send()

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


async def update_settings_ui(change_model_idx: Optional[Union[int, None]] = None):

    # UI elements
    tools_enabled = get_from_config("Tools Enabled")
    user_model_list = get_from_config("User Models List") or []

    model_index = 1
    if change_model_idx is not None:
        model_index = change_model_idx

    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="Model",
                values=AGENT_MODELS + user_model_list,
                # initial_index=AGENT_MODELS.index(model),
                initial_index=change_model_idx or 1,
                description="Select the agent model you want to use.",
            ),
            Switch(
                id="Tools Enabled",
                label="Agent Tools",
                initial=tools_enabled,
                # description="Enable the LLM to call tools",
                tooltip="Enable agent capabilities like tool calling (tools available are listed in src.assistant.tools)",
            ),
            TextInput(
                id="Add Model",
                label="Add Model",
                placeholder="Enter Ollama model name here...",
                description="Add a new model to use from the Ollama server",
                tooltip="Make sure you have pulled the model with `ollama pull <model_name>`!",
                initial=None,
            ),
        ]
    ).send()

    return settings


def run_app():

    from chainlit.cli import run_chainlit
    from chainlit import secret

    run_chainlit(__file__)


def run_ui(queue: Queue):
    from chainlit.cli import run_chainlit
    from chainlit import secret

    secret.chars = queue

    os.environ["CHAINTLIT_HOST"] = CHAINLIT_HOST
    os.environ["CHAINLIT_PORT"] = CHAINLIT_PORT
    run_chainlit(__file__)


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)

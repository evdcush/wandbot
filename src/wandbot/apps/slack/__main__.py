"""A Slack bot that interacts with users and processes their queries.

This module contains the main functionality of the Slack bot. It listens for mentions of the bot in messages,
processes the text of the message, and sends a response. It also handles reactions added to messages and 
saves them as feedback. The bot supports both English and Japanese languages.

The bot uses the Slack Bolt framework for handling events and the langdetect library for language detection.
It also communicates with an external API for processing queries and storing chat history and feedback.

"""

import argparse
import asyncio
import logging
from functools import partial

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web import SlackResponse
from wandbot.api.client import AsyncAPIClient
from wandbot.apps.slack.config import SlackAppEnConfig, SlackAppJaConfig
from wandbot.apps.slack.formatter import MrkdwnFormatter
from wandbot.apps.slack.utils import (
    get_adcopy_blocks,
    get_init_block,
    get_initial_message,
)
from wandbot.apps.utils import format_response
from wandbot.utils import get_logger

logger = get_logger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument(
    "-l",
    "--language",
    default="en",
    help="Language of the bot",
    type=str,
    choices=["en", "ja"],
)

args = parser.parse_args()

if args.language == "ja":
    config = SlackAppJaConfig()
else:
    config = SlackAppEnConfig()


app = AsyncApp(token=config.SLACK_APP_TOKEN)
api_client = AsyncAPIClient(url=config.WANDBOT_API_URL)


async def send_message(
    say: callable, message: str, thread: str = None
) -> SlackResponse:
    message = MrkdwnFormatter()(message)
    if thread is not None:
        return await say(text=message, thread_ts=thread)
    else:
        return await say(text=message)


@app.event("app_mention")
async def handle_mention(
    event: dict, say: callable, logger: logging.Logger
) -> None:
    original_msg_ts = event.get("ts")
    user = event.get("user")
    init_block = get_init_block(user=user)
    say = partial(say, token=config.SLACK_BOT_TOKEN)
    await say(blocks=init_block, thread_ts=original_msg_ts)


@app.action("docsbot")
async def docsbot_handler(
    ack: callable, body: dict, say: callable, logger: logging.Logger
) -> None:
    """
    Handles the command when the app is mentioned in a message.

    Args:
        ack (function): The function to acknowledge the event.
        body (dict): The event body containing the message details.
        say (function): The function to send a message.
        logger (Logger): The logger instance for logging errors.

    Raises:
        Exception: If there is an error posting the message.
    """
    await ack()

    logger.info(f"Received message: {body}")
    initial_message = await get_initial_message(
        app, body["message"], body["channel"].get("id"), config.SLACK_BOT_TOKEN
    )
    logger.info(f"Initial message: {initial_message}")

    try:
        query = initial_message.get("text")
        user = initial_message.get("user")
        thread_id = initial_message.get(
            "thread_ts", None
        ) or initial_message.get("ts", None)
        say = partial(say, token=config.SLACK_BOT_TOKEN)

        chat_history = await api_client.get_chat_history(
            application=config.APPLICATION, thread_id=thread_id
        )

        if not chat_history:
            # send out the intro message
            await send_message(
                say=say,
                message=config.INTRO_MESSAGE.format(user=user),
                thread=thread_id,
            )
        # process the query through the api
        api_response = await api_client.query(
            question=query,
            chat_history=chat_history,
            language=config.bot_language,
            application=config.APPLICATION,
        )
        response = format_response(
            config,
            api_response,
            config.OUTRO_MESSAGE,
        )

        # send the response
        sent_message = await send_message(
            say=say, message=response, thread=thread_id
        )

        await app.client.reactions_add(
            channel=body["channel"].get("id"),
            timestamp=sent_message["ts"],
            name="thumbsup",
            token=config.SLACK_BOT_TOKEN,
        )
        await app.client.reactions_add(
            channel=body["channel"].get("id"),
            timestamp=sent_message["ts"],
            name="thumbsdown",
            token=config.SLACK_BOT_TOKEN,
        )

        #  save the question answer to the database
        await api_client.create_question_answer(
            thread_id=thread_id,
            question_answer_id=sent_message["ts"],
            language=config.bot_language,
            **api_response.model_dump(),
        )

    except Exception as e:
        logger.error(f"Error posting message: {e}")


@app.action("adcopy")
async def adcopy_handler(
    ack: callable, body: dict, say: callable, logger: logging.Logger
) -> None:
    """
    Handles the command when the app is mentioned in a message.
    :param ack:
    :param body:
    :param say:
    :param logger:
    :return:
    """

    await ack()

    logger.info(f"Received message: {body}")
    initial_message = await get_initial_message(
        app, body["message"], body["channel"].get("id"), config.SLACK_BOT_TOKEN
    )
    logger.info(f"Initial message: {initial_message}")

    thread_ts = initial_message.get("thread_ts", None) or initial_message.get(
        "ts", None
    )

    adcopy_blocks = get_adcopy_blocks()

    say = partial(say, token=config.SLACK_BOT_TOKEN)
    await say(blocks=adcopy_blocks, thread_ts=thread_ts)


async def handle_adcopy_action(
    body: dict, say: callable, action: str, persona: str, logger: logging.Logger
) -> None:
    """
    Handles the command when the app is mentioned in a message.
    :param body:
    :param say:
    :param logger:
    :return:
    """

    logger.info(f"Received message: {body}")
    initial_message = await get_initial_message(
        app, body["message"], body["channel"].get("id"), config.SLACK_BOT_TOKEN
    )
    logger.info(f"Initial message: {initial_message}")
    query = initial_message.get("text")
    api_response = await api_client.generate_ads(
        query=query, action=action, persona=persona
    )

    thread_ts = initial_message.get("thread_ts", None) or initial_message.get(
        "ts", None
    )
    say = partial(say, token=config.SLACK_BOT_TOKEN)

    await say(api_response.ad_copies, thread_ts=thread_ts)


@app.action("executive_awareness")
async def executive_awareness_handler(
    ack: callable, body: dict, say: callable, logger: logging.Logger
) -> None:
    await ack()
    await handle_adcopy_action(body, say, "awareness", "executive", logger)


@app.action("executive_signups")
async def executive_signups_handler(
    ack: callable, body: dict, say: callable, logger: logging.Logger
) -> None:
    await ack()
    await handle_adcopy_action(body, say, "signups", "executive", logger)


@app.action("technical_awareness")
async def technical_awareness_handler(
    ack: callable, body: dict, say: callable, logger: logging.Logger
) -> None:
    await ack()
    await handle_adcopy_action(body, say, "awareness", "technical", logger)


@app.action("technical_signups")
async def technical_signups_handler(
    ack: callable, body: dict, say: callable, logger: logging.Logger
) -> None:
    await ack()
    await handle_adcopy_action(body, say, "signups", "technical", logger)


def parse_reaction(reaction: str) -> int:
    """
    Parses the reaction and returns the corresponding rating value.

    Args:
        reaction (str): The reaction emoji.

    Returns:
        int: The rating value (-1, 0, or 1).
    """
    if reaction == "+1":
        return 1
    elif reaction == "-1":
        return -1
    else:
        return 0


@app.event("reaction_added")
async def handle_reaction_added(event: dict) -> None:
    """
    Handles the event when a reaction is added to a message.

    Args:
        event (dict): The event details.

    """
    channel_id = event["item"]["channel"]
    message_ts = event["item"]["ts"]

    conversation = await app.client.conversations_replies(
        channel=channel_id,
        ts=message_ts,
        inclusive=True,
        limit=1,
        token=config.SLACK_BOT_TOKEN,
    )
    messages = conversation.get(
        "messages",
    )
    if messages and len(messages):
        thread_ts = messages[0].get("thread_ts")
        if thread_ts:
            rating = parse_reaction(event["reaction"])
            await api_client.create_feedback(
                feedback_id=event["event_ts"],
                question_answer_id=message_ts,
                rating=rating,
            )


async def main():
    handler = AsyncSocketModeHandler(app, config.SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())

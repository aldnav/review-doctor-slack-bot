import logging
import os
import re
from collections import namedtuple
from datetime import datetime
from functools import cmp_to_key

from dotenv import find_dotenv, load_dotenv
from flask import Flask, Request, abort, request
from slack_bolt import Ack, App, Respond
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from functions import cooler_summary
from utils import verify_slack_request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(find_dotenv())

# Set Slack API credentials
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_USER_ID = os.environ["SLACK_BOT_USER_ID"]

# Initialize the Slack app
app = App(token=SLACK_BOT_TOKEN)

# Initialize the Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


def get_bot_user_id():
    """
    Get the bot user ID using the Slack API.
    Returns:
        str: The bot user ID.
    """
    try:
        # Initialize the Slack client with your bot token
        slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        response = slack_client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        print(f"Error: {e}")


def echo(text):
    """
    Custom function to process the text and return a response.
    In this example, the function converts the input text to uppercase.

    Args:
        text (str): The input text to process.

    Returns:
        str: The processed text.
    """
    response = text.upper()
    return response


@app.event("app_mention")
def handle_mentions(body, say):
    """
    Event listener for mentions in Slack.
    When the bot is mentioned, this function processes the text and sends a response.

    Args:
        body (dict): The event data received from Slack.
        say (callable): A function for sending a response to the channel.
    """
    text = body["event"]["text"]

    mention = f"<@{SLACK_BOT_USER_ID}>"
    text = text.replace(mention, "").strip()

    response = echo(text)
    say(response)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """
    Route for handling Slack events.
    This function passes the incoming HTTP request to the SlackRequestHandler for processing.

    Returns:
        Response: The result of handling the request.
    """
    return handler.handle(request)


PR = namedtuple("PR", "text url target timestamp is_high_priority")


def get_pr(message: str) -> str:
    lines = message.split("\n")
    for line in lines:
        if line.startswith("PR:"):
            return line.split("PR:")[1].strip()
    return message


def get_target(message: str) -> str:
    lines = message.split("\n")
    for line in lines:
        line = line.lower()
        if line.startswith("target:"):
            return line.split("target:")[1].strip()
    return message


def is_high_priority(message: str) -> bool:
    return (
        "high priority" in message.lower()
        or "p1" in message.lower()
        or "emergency" in message.lower()
        or "hotfix" in message.lower()
    )


def sort_scientifically(pr1: PR, pr2: PR) -> int:
    if pr1.is_high_priority and not pr2.is_high_priority:
        return -1
    elif pr2.is_high_priority and not pr1.is_high_priority:
        return 1

    if pr1.target < pr2.target:
        return -1
    elif pr1.target > pr2.target:
        return 1

    if pr1.timestamp < pr2.timestamp:
        return -1
    elif pr1.timestamp > pr2.timestamp:
        return 1

    return 0


def summarize_requests(command):
    """Summarize request for code review from pinned messages in channel"""
    channel_id: str = command.get("channel_id", "")
    slack_client = app.client
    try:
        pinned_messages = slack_client.pins_list(channel=channel_id)
    except SlackApiError as e:
        return "Something went wrong. Please try again later."

    messages = pinned_messages["items"]
    messages = [message["message"] for message in messages]
    PRs = [
        PR(
            text=get_pr(message["text"]),
            url=message["permalink"],
            timestamp=datetime.fromtimestamp(float(message["ts"])),
            target=get_target(message["text"]),
            is_high_priority=is_high_priority(message["text"]),
        )
        for message in messages
        if "PR:" in message["text"] and message["user"] != SLACK_BOT_USER_ID
    ]

    PRs = sorted(PRs, key=cmp_to_key(sort_scientifically))

    if not PRs:
        return "Horray no PRs to review! 🎉"
    summary = """\
    Here's a summary of the PRs that need review\

{pr_count} requests:\

{prs}
    """.format(
        prs="\n".join([f"- <{pr.url}|{pr.text}>" for pr in PRs]),
        pr_count=len(PRs),
    )

    try:
        summary = clean_mrkdwn_links(cooler_summary(summary))
    except Exception as e:
        logger.error(e)
    return summary


def clean_mrkdwn_links(message: str):
    markdown_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    md_links = re.findall(markdown_pattern, message)
    mrkdwn_link_template = "<{url}|{text}>"
    for md_link in md_links:
        message = message.replace(
            f"[{md_link[0]}]({md_link[1]})",
            mrkdwn_link_template.format(url=md_link[1], text=md_link[0]),
        )
    return message


@app.command("/summarize")
def summarize_pr_requests(ack, say, command):
    ack()
    response = summarize_requests(command)
    channel_id: str = command.get("channel_id", "")
    say(text=response, channel=channel_id)


@flask_app.route("/summarize", methods=["POST"])
def listen_to_command_summarize():
    """
    Route for handling Slack events.
    This function passes the incoming HTTP request to the SlackRequestHandler for processing.

    Returns:
        Response: The result of handling the request.
    """
    return handler.handle(request)


# Run the Flask app
if __name__ == "__main__":
    flask_app.run(debug=True)

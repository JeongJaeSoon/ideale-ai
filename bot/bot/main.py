import asyncio
import os
import signal
import time
from enum import Enum
from typing import Any, Dict, List

import openai
import slack_bolt.async_app
import slack_bolt.context.say.async_say
import slack_sdk.web.async_client
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler


class Role(Enum):
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


class ChatEntry:
    def __init__(self, role: Role, content: str):
        self.role = role
        self.content = content


class GPTAgent:
    client: OpenAI

    def __init__(self):
        self.client = OpenAI()

    def generate_stream(self, messages:List[ChatEntry]) -> openai.Stream:
        # TODO: Get model, stream settings from config → Separate config script
        return self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
        )


class SlackBot:
    agent: GPTAgent
    bolt: slack_bolt.async_app.AsyncApp
    slack_bot_member_id: str
    async_socket_mode_handler: AsyncSocketModeHandler

    def __init__(
        self,
        agent: GPTAgent,
        slack_bot_token: str,
        slack_app_token: str,
        slack_signing_secret: str,
        slack_bot_member_id: str,
    ):
        self.agent = agent
        self.bolt = slack_bolt.async_app.AsyncApp(
            token=slack_bot_token,
            signing_secret=slack_signing_secret,
            process_before_response=True,
        )
        self.slack_bot_member_id = slack_bot_member_id
        self.async_socket_mode_handler = AsyncSocketModeHandler(app=self.bolt, app_token=slack_app_token)
        self.setup_event_handlers()

    def setup_event_handlers(self):
        @self.bolt.event("app_mention")
        async def app_mention_handler(
            event: Dict[str, Any],
            client: slack_sdk.web.async_client.AsyncWebClient,
            say: slack_bolt.context.say.async_say.AsyncSay,
        ):
            # Prevent duplicate response
            if time.time() - float(event["event_ts"]) > 3:
                return

            user_id: str = event['user']
            thread_ts: str = event.get('thread_ts') or event['ts']

            replies = await client.conversations_replies(
                channel=event["channel"],
                ts=thread_ts,
            )
            messages = self.__get_messages_from_replies(replies)

            if len(messages) == 0:
                return

            progress = await say(text=":loading_spinner:", thread_ts=thread_ts)
            stream = self.agent.generate_stream(messages)
            response = ""

            for chunk in stream:
                choice = chunk.choices[0]

                # TODO: Implements check choice.finish_reason
                # https://platform.openai.com/docs/guides/text-generation/chat-completions-response-format

                content = choice.delta.content

                if content is not None:
                    response += content
                else:
                    continue

                if not response:
                    continue

                # FIXME: Slack API rate limit → asyncio task
                await client.chat_update(
                    channel=progress["channel"],
                    ts=progress["ts"],
                    text=response,
                )

    def __get_messages_from_replies(self, replies: Dict[str, Any]) -> List[ChatEntry]:
        if replies["messages"] is None:
            return []

        messages = []

        for message in replies["messages"]:
            role = "assistant" if message.get("user") == self.slack_bot_member_id else "user"
            content = message["text"].replace(f"<@{self.slack_bot_member_id}>", "").strip()

            files = message.get("files")

            if files is not None:
                content += "\n"
                content += "\n".join([file.get("url_private_download", "") for file in files])

            if content == "":
                continue

            messages.append({"role": role, "content": content})

        return messages


load_dotenv(override=True)
app: FastAPI = FastAPI()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def socket_mode_handler():
        SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
        SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
        SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
        SLACK_BOT_MEMBER_ID = os.environ["SLACK_BOT_MEMBER_ID"]

        gpt_agent = GPTAgent()
        slack_bot = SlackBot(gpt_agent, SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET, SLACK_BOT_MEMBER_ID)

        task = loop.create_task(slack_bot.async_socket_mode_handler.start_async())

        async def graceful_shutdown():
            await slack_bot.async_socket_mode_handler.close_async()

            inflight_tasks = [
                t for t in asyncio.all_tasks(loop) if t not in [
                    root_task, task, asyncio.current_task(loop)
                ]
            ]
            await asyncio.gather(*inflight_tasks)

            task.cancel()

        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(graceful_shutdown()))

        try:
            await task
        except asyncio.CancelledError:
            pass

    root_task = loop.create_task(socket_mode_handler())
    loop.run_until_complete(root_task)

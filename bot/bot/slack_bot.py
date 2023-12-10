
import time
from typing import Any, Dict

import slack_bolt.async_app
import slack_bolt.context.say.async_say
import slack_sdk.web.async_client
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from bot.agent import Agent
from bot.types.chat_entry import ChatEntries, ChatEntry
from bot.types.slack_info import SlackInfo


class SlackBot:
    agent: Agent
    bolt: slack_bolt.async_app.AsyncApp
    slack_bot_member_id: str
    async_socket_mode_handler: AsyncSocketModeHandler

    def __init__(self, agent: Agent, slack_info: SlackInfo):
        self.agent = agent
        self.bolt = slack_bolt.async_app.AsyncApp(
            token=slack_info.slack_bot_token,
            signing_secret=slack_info.slack_signing_secret,
            process_before_response=True,
        )
        self.slack_bot_member_id = slack_info.slack_bot_member_id
        self.async_socket_mode_handler = AsyncSocketModeHandler(app=self.bolt, app_token=slack_info.slack_app_token)
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
            messages: ChatEntries = self.__get_messages_from_replies(replies)

            if messages.length == 0:
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
                # slack_sdk.errors.SlackApiError: The request to the Slack API failed. (url: https://www.slack.com/api/chat.update, status: 429)
                # The server responded with: {'ok': False, 'error': 'ratelimited'}
                await client.chat_update(
                    channel=progress["channel"],
                    ts=progress["ts"],
                    text=response,
                )

    def __get_messages_from_replies(self, replies: Dict[str, Any]) -> ChatEntries:
        if replies["messages"] is None:
            return ChatEntries([])

        messages = ChatEntries([])

        for message in replies["messages"]:
            role = "assistant" if message.get("user") == self.slack_bot_member_id else "user"
            content = message["text"].replace(f"<@{self.slack_bot_member_id}>", "").strip()

            files = message.get("files")

            if files is not None:
                content += "\n"
                content += "\n".join([file.get("url_private_download", "") for file in files])

            if content == "":
                continue

            messages.append(ChatEntry(role=role, content=content))

        return messages

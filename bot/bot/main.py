import asyncio
import os
import signal

from dotenv import load_dotenv
from fastapi import FastAPI

from bot.agent import Agent
from bot.slack_bot import SlackBot
from bot.types.slack_info import SlackInfo

load_dotenv(override=True)
app: FastAPI = FastAPI()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def socket_mode_handler():
        slack_info: SlackInfo = SlackInfo(
            slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
            slack_app_token=os.environ["SLACK_APP_TOKEN"],
            slack_signing_secret=os.environ["SLACK_SIGNING_SECRET"],
            slack_bot_member_id=os.environ["SLACK_BOT_MEMBER_ID"],
        )

        slack_bot = SlackBot(
            agent=Agent(),
            slack_info=slack_info,
        )

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

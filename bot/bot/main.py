import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

class SlackBot:
    def __init__(self, bot_token: str, app_token: str):
        self.app = App(token=bot_token)
        self.handler = SlackRequestHandler(self.app)
        self.socket_mode_handler = SocketModeHandler(app=self.app, app_token=app_token)

    def start_socket_mode(self):
        self.socket_mode_handler.start()

    def setup_event_handlers(self):
        @self.app.event("app_mention")
        def mention_handler(event: dict, say):
            user_id: str = event['user']
            thread_ts: str = event.get('thread_ts') or event['ts']
            say(text=f"<@{user_id}>님이 호출하셨습니다!", thread_ts=thread_ts)

SLACK_BOT_TOKEN: str = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN: str = os.environ.get("SLACK_APP_TOKEN", "")

slack_bot: SlackBot = SlackBot(SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
slack_bot.setup_event_handlers()

app: FastAPI = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request):
    return await slack_bot.handler.handle(request)

if __name__ == "__main__":
    slack_bot.start_socket_mode()

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from openai import OpenAI
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

class GPTAgent:
    def __init__(self):
        self.client = OpenAI()

    def generate_response(self, input_text: str) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": input_text}
            ],
        )

        return completion.choices[0].message.content

class SlackBot:
    def __init__(self, agent: GPTAgent):
        self.app = App()
        self.handler = SlackRequestHandler(self.app)
        self.socket_mode_handler = SocketModeHandler(app=self.app)
        self.agent = agent

    def start_socket_mode(self):
        self.socket_mode_handler.start()

    def setup_event_handlers(self):
        @self.app.event("app_mention")
        def handle_app_mention(event: dict, say):
            user_id: str = event['user']
            thread_ts: str = event.get('thread_ts') or event['ts']

            response = self.agent.generate_response(event['text'])
            say(text=response, thread_ts=thread_ts)

gpt_agent: GPTAgent = GPTAgent()
slack_bot: SlackBot = SlackBot(gpt_agent)
slack_bot.setup_event_handlers()

app: FastAPI = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request):
    return await slack_bot.handler.handle(request)

if __name__ == "__main__":
    slack_bot.start_socket_mode()

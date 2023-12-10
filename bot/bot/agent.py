import openai
from openai import OpenAI

from bot.types.chat_entry import ChatEntries


class Agent:
    client: OpenAI

    def __init__(self):
        self.client = OpenAI()

    def generate_stream(self, messages:ChatEntries) -> openai.Stream:
        # TODO: Get model, stream settings from config → Separate config script
        return self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages.to_json(),
            temperature=1.0,
            stream=True,
        )

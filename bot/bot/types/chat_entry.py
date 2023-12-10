from enum import Enum
from typing import List


class Role(Enum):
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


class ChatEntry:
    role: Role
    content: str

    def __init__(self, role: Role, content: str):
        self.role = role
        self.content = content

    def to_json(self):
        return {
            "role": self.role,
            "content": self.content
        }


class ChatEntries:
    entries: List[ChatEntry]
    length: int

    def __init__(self, entries: List[ChatEntry]):
        self.entries = entries
        self.length = len(entries)

    def append(self, entry: ChatEntry):
        self.entries.append(entry)
        self.length += 1

    def to_json(self):
        return [entry.to_json() for entry in self.entries]

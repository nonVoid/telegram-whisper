import os
from typing import Literal, Optional

import whisper
from telethon import TelegramClient, events
from telethon.tl.custom import Message
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Use your own values from my.telegram.org
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
client = TelegramClient('bot', API_ID, API_HASH)


@dataclass
class VoiceMessageReturn:
    file_path: str
    chat_id: str
    reply_msg: Message


class WhisperGerman:
    def __init__(self, telegram_client: TelegramClient, model_name: Literal["large-v2", "medium", "base", "small"]):
        self.client = telegram_client
        self.model = whisper.load_model(model_name)

    async def load_voice_message(self, event: events.NewMessage.Event) -> Optional[VoiceMessageReturn]:
        if event.message.mentioned:
            if event.message.reply_to_msg_id is None:
                return None

            message_list = await self.client.get_messages(event.chat_id, ids=(event.message.reply_to_msg_id,))
            if message_list.total == 0:
                return None
            message: Message = message_list[0]
        else:
            message = event.message
        if not message.voice:
            return None

        file_path = await self._download_voice_message(message=message)
        return VoiceMessageReturn(file_path=file_path, chat_id=event.message.chat_id, reply_msg=message)

    @staticmethod
    async def _download_voice_message(message: Message) -> str:
        return await message.download_media(file="tmp/")

    def transcribe(self, file_path: str):
        result = self.model.transcribe(file_path)
        print(result)
        return result["text"]

    async def send_message(self, chat_id: str, reply_to: Optional[Message], message: str):
        await self.client.send_message(entity=chat_id, reply_to=reply_to, message=message)

    async def process(self, event: events.NewMessage.Event):
        print(event)
        voice_return_data = await self.load_voice_message(event=event)
        if voice_return_data is None:
            return
        transcription = self.transcribe(file_path=voice_return_data.file_path)
        os.remove(path=voice_return_data.file_path)
        await self.send_message(chat_id=voice_return_data.chat_id, reply_to=voice_return_data.reply_msg,
                                message=transcription)


whisper_german = WhisperGerman(telegram_client=client, model_name="large-v2")


@client.on(events.NewMessage())
async def my_event_handler(event: events.NewMessage.Event):
    await whisper_german.process(event=event)


client.start(bot_token=BOT_TOKEN)
print("Started")
client.run_until_disconnected()

import os
import json
import asyncio
import websockets
import sounddevice as sd

SAMPLE_RATE = 16000
URL = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&model=nova-2&punctuate=true"


def load_env():
    with open(".env") as f:
        for line in f:
            if line.startswith("DEEPGRAM_API_KEY"):
                return line.strip().split("=")[1]


API_KEY = load_env()


async def run():

    async with websockets.connect(
        URL,
        additional_headers={"Authorization": f"Token {API_KEY}"}
    ) as ws:

        loop = asyncio.get_running_loop()

        transcripts = []

        def audio_callback(indata, frames, time, status):
            asyncio.run_coroutine_threadsafe(
                ws.send(indata.tobytes()),
                loop
            )

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=audio_callback
        )

        stream.start()

        async def receive():
            async for message in ws:
                data = json.loads(message)

                try:
                    transcript = data["channel"]["alternatives"][0]["transcript"]

                    if transcript:
                        transcripts.append(transcript)

                except KeyError:
                    pass

        receiver = asyncio.create_task(receive())

        # record for 10 seconds
        await asyncio.sleep(10)

        receiver.cancel()
        stream.stop()

        return " ".join(transcripts)
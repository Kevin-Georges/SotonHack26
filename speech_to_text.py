import os
import json
import asyncio
import websockets
import sounddevice as sd

SAMPLE_RATE = 16000
URL = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&model=nova-2&interim_results=true&punctuate=true"


def load_env():
    with open(".env") as f:
        for line in f:
            if line.startswith("DEEPGRAM_API_KEY"):
                return line.strip().split("=")[1]


API_KEY = load_env()

if not API_KEY:
    raise RuntimeError("DEEPGRAM_API_KEY not found in .env")


async def run():

    async with websockets.connect(
        URL,
        additional_headers={"Authorization": f"Token {API_KEY}"}
    ) as ws:

        print("\nListening... speak into your microphone\n")

        loop = asyncio.get_running_loop()

        def audio_callback(indata, frames, time, status):
            if status:
                print(status)

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

        async for message in ws:

            data = json.loads(message)

            try:
                # Only print final transcripts
                if data.get("is_final"):
                    transcript = data["channel"]["alternatives"][0]["transcript"]

                    if transcript:
                        print(transcript)

            except KeyError:
                pass


if __name__ == "__main__":
    asyncio.run(run())
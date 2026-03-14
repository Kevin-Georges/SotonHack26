import os
import json
import random
import asyncio
import websockets
import sounddevice as sd

# -------------------------------
# CONFIG
# -------------------------------

SAMPLE_RATE = 16000
URL = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&model=nova-2&punctuate=true"


# -------------------------------
# LOAD API KEY
# -------------------------------

def load_env():
    with open(".env") as f:
        for line in f:
            if line.startswith("DEEPGRAM_API_KEY"):
                return line.strip().split("=")[1]


API_KEY = load_env()


# -------------------------------
# SENTENCE GENERATOR
# -------------------------------

subjects = [
    "the quick fox",
    "a tired student",
    "the curious robot",
    "an old scientist",
]

verbs = [
    "jumps over",
    "studies",
    "carefully examines",
    "quietly watches",
]

objects = [
    "the glowing computer",
    "a mysterious signal",
    "the strange machine",
    "a complicated puzzle",
]

endings = [
    "late at night",
    "during the experiment",
    "while everyone is sleeping",
    "without making a sound",
]


def generate_sentence():
    sentence = (
        random.choice(subjects) + " " +
        random.choice(verbs) + " " +
        random.choice(objects) + " " +
        random.choice(endings)
    )

    return sentence.capitalize() + "."


# -------------------------------
# ACCURACY CHECK
# -------------------------------

def calculate_accuracy(expected, spoken):

    expected_words = expected.lower().replace(".", "").split()
    spoken_words = spoken.lower().replace(".", "").split()

    matches = 0

    for word in expected_words:
        if word in spoken_words:
            matches += 1

    accuracy = matches / len(expected_words)

    return accuracy


# -------------------------------
# SPEECH TO TEXT (DEEPGRAM)
# -------------------------------

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


# -------------------------------
# MAIN PROGRAM
# -------------------------------

async def main():

    sentence = generate_sentence()

    print("\nPlease read the following sentence aloud:\n")
    print(sentence)
    print("\nListening...\n")

    transcript = await run()

    print("\nExpected:")
    print(sentence)

    print("\nDetected:")
    print(transcript)

    accuracy = calculate_accuracy(sentence, transcript)

    print(f"\nAccuracy Score: {accuracy:.2%}")


if __name__ == "__main__":
    asyncio.run(main())

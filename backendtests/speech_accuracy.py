import os
import json
import random
import asyncio
import websockets
import sounddevice as sd
import tkinter as tk
import time
import random

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

def run_mouse_game():
    import tkinter as tk
    import time
    import math

    WIDTH = 900
    HEIGHT = 500
    DURATION = 10  # seconds

    root = tk.Tk()
    root.title("Mouse Tracking Challenge")

    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
    canvas.pack()

    meter = tk.Label(root, text="Accuracy: 0.0%", font=("Arial", 14))
    meter.pack()

    amplitude = HEIGHT / 3
    center = HEIGHT / 2
    frequency = 0.02
    speed = 3

    line_points = []
    start_time = time.time()

    total_error = 0
    samples = 0

    def update():
        nonlocal total_error, samples

        elapsed = time.time() - start_time
        if elapsed >= DURATION:
            finish()
            return

        t = elapsed * 100
        x = WIDTH
        y = center + amplitude * math.sin(t * frequency)

        line_points.append((x, y))

        for i in range(len(line_points)):
            px, py = line_points[i]
            line_points[i] = (px - speed, py)

        while line_points and line_points[0][0] < 0:
            line_points.pop(0)

        canvas.delete("line")

        for i in range(len(line_points) - 1):
            x1, y1 = line_points[i]
            x2, y2 = line_points[i + 1]
            canvas.create_line(x1, y1, x2, y2, fill="cyan", width=3, tags="line")

        mouse_x = root.winfo_pointerx() - root.winfo_rootx()
        mouse_y = root.winfo_pointery() - root.winfo_rooty()

        if line_points:
            closest = min(line_points, key=lambda p: abs(p[0] - mouse_x))
            dist = abs(mouse_y - closest[1])

            total_error += dist
            samples += 1

        canvas.delete("cursor")
        canvas.create_oval(
            mouse_x - 5, mouse_y - 5,
            mouse_x + 5, mouse_y + 5,
            fill="white",
            tags="cursor"
        )

        if samples > 0:
            avg_error = total_error / samples
            accuracy = max(0, 100 - avg_error / 2)
            meter.config(text=f"Accuracy: {accuracy:.1f}%")

        root.after(16, update)

    def finish():
        canvas.delete("all")

        if samples > 0:
            avg_error = total_error / samples
            accuracy = max(0, 100 - avg_error / 2)
        else:
            accuracy = 0

        canvas.create_text(
            WIDTH/2,
            HEIGHT/2,
            text=f"Final Accuracy: {accuracy:.1f}%",
            fill="white",
            font=("Arial", 30)
        )
        # close window after 2 seconds
        root.after(2000, root.destroy)

    update()
    root.mainloop()
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

    print("\nStarting mouse tracking game...\n")

    run_mouse_game()


if __name__ == "__main__":
    asyncio.run(main())

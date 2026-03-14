import cv2
import os
import json
import random
import asyncio
import websockets
import sounddevice as sd
import time
import math
import threading
import secrets
import string

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================================================
# CONFIG
# =========================================================

SAMPLE_RATE = 16000
URL = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&model=nova-2&punctuate=true"

# =========================================================
# GLOBAL FACE MONITOR STATE
# =========================================================

face_count = 0
face_lock = threading.Lock()
stop_face_monitor = threading.Event()
face_thread = None

# =========================================================
# GLOBAL TEST STATE
# =========================================================

test_state = {
    "running": False,
    "phase": "idle",
    "message": "Waiting to start.",
    "sentence": "",
    "transcript": "",
    "speech_accuracy": None,
    "mouse_accuracy": None,
    "average_accuracy": None,
    "passed": False,
    "key": "",
    "error": "",
}

state_lock = threading.Lock()

# =========================================================
# GLOBAL WEB MOUSE GAME STATE
# =========================================================

mouse_game_state = {
    "active": False,
    "status": "idle",
    "width": 900,
    "height": 500,
    "line_points": [],
    "mouse_x": 450,
    "mouse_y": 250,
    "accuracy": 0.0,
    "remaining": 0.0,
    "pause_text": "",
    "finished": False,
}

mouse_game_lock = threading.Lock()

# =========================================================
# KEY STORAGE
# =========================================================

active_keys = {}

# =========================================================
# LOAD API KEY
# =========================================================

def load_env():
    env_key = os.environ.get("DEEPGRAM_API_KEY")
    if env_key:
        return env_key.strip().strip('"').strip("'")

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    if not os.path.exists(env_path):
        print("WARNING: DEEPGRAM_API_KEY not found.")
        print("Create a .env file with: DEEPGRAM_API_KEY=your_key_here")
        print("Or set environment variable: set DEEPGRAM_API_KEY=your_key_here")
        return None

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("DEEPGRAM_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    print("WARNING: DEEPGRAM_API_KEY not found.")
    print("Create a .env file with: DEEPGRAM_API_KEY=your_key_here")
    print("Or set environment variable: set DEEPGRAM_API_KEY=your_key_here")
    return None


API_KEY = load_env()

if API_KEY:
    print("Deepgram key loaded.")
else:
    print("Using placeholder key - speech recognition will not work.")

# =========================================================
# HELPERS
# =========================================================

def update_state(**kwargs):
    with state_lock:
        for key, value in kwargs.items():
            test_state[key] = value


def get_state_copy():
    with state_lock:
        return dict(test_state)


def reset_test_state():
    update_state(
        running=False,
        phase="idle",
        message="Waiting to start.",
        sentence="",
        transcript="",
        speech_accuracy=None,
        mouse_accuracy=None,
        average_accuracy=None,
        passed=False,
        key="",
        error=""
    )


def update_mouse_game_state(**kwargs):
    with mouse_game_lock:
        for key, value in kwargs.items():
            mouse_game_state[key] = value


def get_mouse_game_state_copy():
    with mouse_game_lock:
        return dict(mouse_game_state)


def reset_mouse_game_state():
    update_mouse_game_state(
        active=False,
        status="idle",
        width=900,
        height=500,
        line_points=[],
        mouse_x=450,
        mouse_y=250,
        accuracy=0.0,
        remaining=0.0,
        pause_text="",
        finished=False,
    )

# =========================================================
# KEY HELPERS
# =========================================================

def cleanup_expired_keys():
    current_time = time.time()
    expired = [k for k, v in active_keys.items() if current_time > v]
    for k in expired:
        del active_keys[k]


def generate_16_digit_key():
    return ''.join(secrets.choice(string.digits) for _ in range(16))

# =========================================================
# FACE MONITOR
# =========================================================

def face_monitor():
    global face_count

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        update_state(
            running=False,
            phase="error",
            error="Could not open webcam.",
            message="Could not open webcam."
        )
        stop_face_monitor.set()
        return

    while not stop_face_monitor.is_set():
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(100, 100)
        )

        with face_lock:
            face_count = len(faces)
            current_count = face_count

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(
            frame,
            f"Faces: {current_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )

        if current_count > 1:
            status_text = "TEST PAUSED - MULTIPLE PEOPLE DETECTED"
            color = (0, 0, 255)
        elif current_count == 0:
            status_text = "TEST PAUSED - NO FACE DETECTED"
            color = (0, 165, 255)
        else:
            status_text = "TEST RUNNING"
            color = (0, 255, 0)

        cv2.putText(
            frame,
            status_text,
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

        cv2.imshow("Face Count Monitor", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):
            stop_face_monitor.set()
            break

    cap.release()
    cv2.destroyAllWindows()


def get_face_count():
    with face_lock:
        return face_count


def is_test_allowed():
    return get_face_count() == 1


def ensure_face_monitor_running():
    global face_thread

    if face_thread is None or not face_thread.is_alive():
        stop_face_monitor.clear()
        face_thread = threading.Thread(target=face_monitor, daemon=True)
        face_thread.start()

# =========================================================
# SENTENCE GENERATOR
# =========================================================

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

# =========================================================
# ACCURACY CHECK
# =========================================================

def calculate_accuracy(expected, spoken):
    expected_words = expected.lower().replace(".", "").split()
    spoken_words = spoken.lower().replace(".", "").split()

    matches = 0
    for word in expected_words:
        if word in spoken_words:
            matches += 1

    return matches / len(expected_words)

# =========================================================
# SPEECH TO TEXT (DEEPGRAM)
# =========================================================

async def run_speech_test():
    if not API_KEY:
        raise Exception("Deepgram API key missing. Check your .env file.")

    test_duration = 10

    update_state(
        phase="speech",
        message="Speech test started. Read the sentence aloud."
    )

    async with websockets.connect(
        URL,
        additional_headers={"Authorization": f"Token {API_KEY}"}
    ) as ws:
        loop = asyncio.get_running_loop()
        transcripts = []

        def audio_callback(indata, frames, time_info, status):
            if is_test_allowed():
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
                    if transcript and is_test_allowed():
                        transcripts.append(transcript)
                        update_state(transcript=" ".join(transcripts))
                except KeyError:
                    pass

        receiver = asyncio.create_task(receive())

        active_time = 0.0
        last_time = time.time()

        while active_time < test_duration and not stop_face_monitor.is_set():
            now = time.time()
            dt = now - last_time
            last_time = now

            current_faces = get_face_count()

            if current_faces == 1:
                active_time += dt
                remaining = max(0, test_duration - active_time)
                update_state(message=f"Speech test running... {remaining:.1f}s remaining")
            elif current_faces > 1:
                update_state(message="Speech test paused: multiple people detected")
            else:
                update_state(message="Speech test paused: no face detected")

            await asyncio.sleep(0.05)

        receiver.cancel()
        stream.stop()
        stream.close()

        return " ".join(transcripts)

# =========================================================
# WEB MOUSE TRACKING GAME
# =========================================================

def run_mouse_game():
    width = 900
    height = 500
    duration = 10

    amplitude = height / 3
    center = height / 2
    frequency = 0.02
    speed = 3

    line_points = []
    total_error = 0
    samples = 0
    active_time = 0.0
    last_time = time.time()
    final_accuracy = 0.0

    reset_mouse_game_state()
    update_mouse_game_state(
        active=True,
        status="running",
        width=width,
        height=height,
        remaining=duration,
        line_points=[],
        finished=False
    )

    update_state(
        phase="mouse",
        message="Mouse test started. Follow the line in the webpage."
    )

    while active_time < duration and not stop_face_monitor.is_set():
        now = time.time()
        dt = now - last_time
        last_time = now

        allowed = is_test_allowed()
        current_faces = get_face_count()

        pause_text = ""

        if allowed:
            active_time += dt

            t = active_time * 100
            x = width
            y = center + amplitude * math.sin(t * frequency)

            line_points.append((x, y))

            for i in range(len(line_points)):
                px, py = line_points[i]
                line_points[i] = (px - speed, py)

            while line_points and line_points[0][0] < 0:
                line_points.pop(0)

            state = get_mouse_game_state_copy()
            mouse_x = state["mouse_x"]
            mouse_y = state["mouse_y"]

            if line_points:
                closest = min(line_points, key=lambda p: abs(p[0] - mouse_x))
                dist = abs(mouse_y - closest[1])
                total_error += dist
                samples += 1

            if samples > 0:
                avg_error = total_error / samples
                accuracy = max(0, 100 - avg_error / 2)
            else:
                accuracy = 0.0

            update_state(
                mouse_accuracy=round(accuracy, 1),
                message=f"Mouse test running... {max(0, duration - active_time):.1f}s remaining"
            )

            update_mouse_game_state(
                active=True,
                status="running",
                line_points=[{"x": p[0], "y": p[1]} for p in line_points],
                accuracy=round(accuracy, 1),
                remaining=max(0, duration - active_time),
                pause_text="",
                finished=False
            )

        else:
            if current_faces > 1:
                pause_text = "PAUSED\nMULTIPLE PEOPLE DETECTED"
                update_state(message="Mouse test paused: multiple people detected")
            elif current_faces == 0:
                pause_text = "PAUSED\nNO FACE DETECTED"
                update_state(message="Mouse test paused: no face detected")
            else:
                pause_text = "PAUSED"
                update_state(message="Mouse test paused")

            if samples > 0:
                avg_error = total_error / samples
                current_accuracy = max(0, 100 - avg_error / 2)
            else:
                current_accuracy = 0.0

            update_mouse_game_state(
                active=True,
                status="paused",
                line_points=[{"x": p[0], "y": p[1]} for p in line_points],
                accuracy=round(current_accuracy, 1),
                remaining=max(0, duration - active_time),
                pause_text=pause_text,
                finished=False
            )

        time.sleep(0.016)

    if samples > 0:
        avg_error = total_error / samples
        final_accuracy = max(0, 100 - avg_error / 2)
    else:
        final_accuracy = 0.0

    update_state(mouse_accuracy=round(final_accuracy, 1))

    update_mouse_game_state(
        active=False,
        status="finished",
        line_points=[{"x": p[0], "y": p[1]} for p in line_points],
        accuracy=round(final_accuracy, 1),
        remaining=0.0,
        pause_text="",
        finished=True
    )

    return final_accuracy

# =========================================================
# TEST RUNNER
# =========================================================

async def run_full_test():
    try:
        reset_test_state()
        reset_mouse_game_state()

        update_state(
            running=True,
            phase="waiting_for_face",
            message="Waiting for exactly 1 face before starting..."
        )

        ensure_face_monitor_running()

        while not stop_face_monitor.is_set():
            if is_test_allowed():
                break
            await asyncio.sleep(0.1)

        if stop_face_monitor.is_set():
            update_state(
                running=False,
                phase="stopped",
                message="Test stopped."
            )
            return

        sentence = generate_sentence()
        update_state(
            sentence=sentence,
            phase="speech",
            message="Please read the sentence aloud."
        )

        transcript = await run_speech_test()
        speech_accuracy = calculate_accuracy(sentence, transcript) * 100

        update_state(
            transcript=transcript,
            speech_accuracy=round(speech_accuracy, 1),
            phase="speech_complete",
            message=f"Speech test complete. Score: {speech_accuracy:.1f}%. Mouse test starting shortly..."
        )

        await asyncio.sleep(2)

        update_state(
            phase="mouse",
            message="Mouse test starting now. Follow the line in the webpage."
        )

        mouse_accuracy = run_mouse_game()

        average_accuracy = (speech_accuracy + mouse_accuracy) / 2
        passed_tests = average_accuracy > 70

        generated_key = ""
        if passed_tests:
            cleanup_expired_keys()
            generated_key = generate_16_digit_key()
            expiration_time = time.time() + (5 * 60)
            active_keys[generated_key] = expiration_time

            print(f"[GENERATED] New key created after passed test: {generated_key}")
            print(f"[SYSTEM] Total active keys in pool: {len(active_keys)}")

        update_state(
            running=False,
            phase="complete",
            mouse_accuracy=round(mouse_accuracy, 1),
            average_accuracy=round(average_accuracy, 1),
            passed=passed_tests,
            key=generated_key,
            message="All tests complete."
        )

    except Exception as e:
        update_state(
            running=False,
            phase="error",
            error=str(e),
            message=f"Error: {e}"
        )
    finally:
        stop_face_monitor.set()
        await asyncio.sleep(0.3)
        cv2.destroyAllWindows()


def background_test_runner():
    asyncio.run(run_full_test())

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start-test", methods=["POST"])
def start_test():
    current = get_state_copy()

    if current["running"]:
        return jsonify({"ok": False, "message": "Test already running."}), 400

    stop_face_monitor.clear()
    reset_test_state()
    reset_mouse_game_state()

    thread = threading.Thread(target=background_test_runner, daemon=True)
    thread.start()

    return jsonify({"ok": True, "message": "Test started."})


@app.route("/status", methods=["GET"])
def status():
    return jsonify(get_state_copy())


@app.route("/mouse-state", methods=["GET"])
def mouse_state():
    return jsonify(get_mouse_game_state_copy())


@app.route("/mouse-move", methods=["POST"])
def mouse_move():
    data = request.json or {}

    try:
        x = float(data.get("x", 0))
        y = float(data.get("y", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Invalid mouse coordinates."}), 400

    state = get_mouse_game_state_copy()
    width = state["width"]
    height = state["height"]

    x = max(0, min(width, x))
    y = max(0, min(height, y))

    update_mouse_game_state(mouse_x=x, mouse_y=y)
    return jsonify({"ok": True})


@app.route("/generate", methods=["POST", "GET"])
def generate_key():
    cleanup_expired_keys()

    new_key = generate_16_digit_key()
    expiration_time = time.time() + (5 * 60)
    active_keys[new_key] = expiration_time

    print(f"[GENERATED] New key created: {new_key}")
    print(f"[SYSTEM] Total active keys in pool: {len(active_keys)}")

    return jsonify({"key": new_key, "expires_in_minutes": 5}), 200


@app.route("/validate", methods=["POST"])
def validate_key():
    cleanup_expired_keys()

    data = request.json
    if not data or "key" not in data:
        return jsonify({"valid": False, "message": "No key provided"}), 400

    client_key = data.get("key", "").strip()

    if client_key in active_keys:
        del active_keys[client_key]
        print(f"[VALIDATED] Key consumed and destroyed: {client_key}")
        return jsonify({"valid": True, "message": "Cart unlocked!"}), 200

    print(f"[REJECTED] Invalid key attempted: {client_key}")
    return jsonify({"valid": False, "message": "Invalid or expired key."}), 401


@app.route("/test-key", methods=["GET"])
def test_key():
    state = get_state_copy()

    if state["passed"] and state["key"]:
        return jsonify({"ok": True, "key": state["key"]}), 200

    return jsonify({"ok": False, "message": "Tests not passed yet."}), 403


if __name__ == "__main__":
    reset_test_state()
    reset_mouse_game_state()
    app.run(host="0.0.0.0", port=2600, debug=False)

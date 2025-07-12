import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, time as dt_time
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# List of prompts
PROMPTS = [
    """
Here’s a list of my time-stamped mood entries for today, along with little notes I wrote in the moment.
Write a warm, personal diary entry in the first person, as if I’m gently reflecting on my day at bedtime.
Do not include the exact times—just write naturally from morning to night.

In the **first paragraph**, describe how my day unfolded emotionally, using poetic or metaphorical language where it feels right. Let it flow like a calm, soft story from the start of my day to the end.

In the **second paragraph**, reflect on both my emotional wins and the difficult moments—what felt good, what didn’t, and how I handled it all.

In the **third paragraph**, help me think about a small resolution or personal intention I could carry into tomorrow based on today’s experience.

Finally, end with:
"Overall, today I was [MOOD]"

Select [MOOD] from this exact list:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Mood entries:
{mood_entries}
""",
    """
Imagine I’m writing in my private journal before bed, reflecting on the emotional journey of my day.
Use the time-stamped moods and notes to help me remember how I felt, but don’t include the exact times in the writing.

Start with a **first paragraph** that gently narrates how my feelings changed throughout the day, like a story told softly to myself. Include light poetic or emotional language when it fits.

In the **second paragraph**, help me reflect on what went well and what didn’t—both the successes and the emotional struggles.

In the **third paragraph**, offer a small piece of personal insight or a resolution I might take into tomorrow, based on what I’ve experienced today.

Then end with this line:
"Overall, today I was [MOOD]"

Choose [MOOD] from:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Entries:
{mood_entries}
""",
    """
I’ve saved my mood entries for today—each with a note from the heart.
Can you help me turn these into a soft, emotional journal entry?

In the **first paragraph**, write as if I’m recalling my day from beginning to end, flowing through the emotions without listing the times. Keep the voice human, warm, and lightly poetic.

In the **second paragraph**, reflect on my emotional highs and lows—where I found comfort or joy, and where I felt stuck or overwhelmed.

In the **third paragraph**, help me draw a small resolution from today’s experience, something gentle I can aim for tomorrow.

At the end, write:
"Overall, today I was [MOOD]"

Pick [MOOD] from:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Mood entries:
{mood_entries}
""",
    """
I’ve collected some mood entries from today—each with how I felt and a small note.
Can you write a reflective journal entry in the first person?

In the **first paragraph**, take me through the story of my day emotionally, starting from morning to night. Leave out the timestamps. Use soft, expressive, and slightly poetic language.

In the **second paragraph**, reflect honestly on my emotional successes and setbacks—what gave me peace or pride, and what challenged or drained me.

In the **third paragraph**, suggest a gentle resolution I can carry into tomorrow, drawn from what I’ve learned about myself today.

Then, on a new line, conclude with:
"Overall, today I was [MOOD]"

Choose [MOOD] from:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Diary entries:
{mood_entries}
"""
]


NOTIFICATION_TITLES = [
    "Mood check 🕵️",
    "Time for a vibe check!",
    "Take a breath 🧘",
    "How are you, really?",
    "Let's log your mood 🌈",
    "Reflect for a moment 🪞",
    "Mindful minute ⏳"
]

NOTIFICATION_BODIES = [
    "How are you feeling today?",
    "Take a moment to reflect 🌤",
    "Your mood matters — let's note it!",
    "Share how your day's going 😊",
    "What's on your mind right now?",
    "Pause and check in with yourself 💭",
    "A quick mood update helps track your wellness!"
]


@app.route("/")
def home():
    return "Flask app is running!"



@app.route("/api/mood-diary", methods=["POST"])
def mood_diary():
    print("Received POST /api/mood-diary")
    data = request.get_json(force=True)

    if not data:
        return jsonify({"error": "Invalid or missing JSON data"}), 400

    moods = data.get("moods", [])
    device_id = data.get("device_id")
    date_str = data.get("date")  # ← Get date from client

    if not moods:
        return jsonify({"error": "No moods provided"}), 400
    if not device_id:
        return jsonify({"error": "No device_id provided"}), 400
    if not date_str:
        return jsonify({"error": "No date provided"}), 400  # Optional but safer

    # Format the mood entries
    mood_entries = "\n".join(
        f"{datetime.fromtimestamp(m['timestamp'] / 1000).strftime('%H:%M')} {m['label']}: {m['note']}"
        for m in moods
    )

    selected_prompt = random.choice(PROMPTS).format(mood_entries=mood_entries)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(selected_prompt)
        print("Gemini response:", response.text)

        # Save diary to Firestore under the provided date
        diary_ref = db.collection("user_diaries").document(device_id)
        diary_ref.set({
            date_str: {
                "summary": response.text,
                "moods": moods
            }
        }, merge=True)

        return jsonify({"summary": response.text})
    except Exception as e:
        print("Error from Gemini:", e)
        return jsonify({"error": "Failed to generate summary"}), 500

# for development
cred = credentials.Certificate("./mood-diary-f25f9-firebase-adminsdk-fbsvc-87ffa83797.json")

# for production
# cred = credentials.Certificate("/etc/secrets/mood-diary-f25f9-firebase-adminsdk-fbsvc-87ffa83797.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/api/register_token", methods=["POST"])
def register_token():
    try:
        data = request.get_json()
        token = data.get("token")
        device_id = data.get("device_id")

        if not device_id:
            return jsonify({"error": "No device_id provided"}), 400

        # If token is None (not sent at all), treat as empty string
        if token is None:
            token = ""

        db.collection("push_tokens").document(device_id).set({
            "token": token,
            "device_id": device_id,
            "notifications_enabled": bool(token),  # optional flag
            "updated_at": firestore.SERVER_TIMESTAMP
        })

        print(f"Registered token: {token} for device: {device_id}")

        return jsonify({"status": "success", "token": token, "device_id": device_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/save_mood", methods=["POST"])
def save_mood():
    try:
        data = request.get_json()
        device_id = data.get("device_id")
        mood = data.get("mood")  # should be a dict with emoji, label, note, timestamp

        if not device_id or not mood:
            return jsonify({"error": "Missing device_id or mood"}), 400

        date_str = datetime.fromtimestamp(mood["timestamp"] / 1000).strftime("%Y-%m-%d")
        doc_ref = db.collection("user_moods").document(device_id)
        doc = doc_ref.get()
        moods_by_date = doc.to_dict() if doc.exists else {}
        if moods_by_date is None:
            moods_by_date = {}

        moods_for_day = moods_by_date.get(date_str, [])
        moods_for_day.append(mood)
        # Use merge=True to avoid overwriting unrelated data
        doc_ref.set({date_str: moods_for_day}, merge=True)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/generate-diary-for-date", methods=["POST"])
def generate_diary_for_date():
    data = request.get_json(force=True)
    device_id = data.get("device_id")
    date = data.get("date")  # format: YYYY-MM-DD

    if not device_id or not date:
        return jsonify({"error": "Missing device_id or date"}), 400

    # Get moods for that date
    moods_doc = db.collection("user_moods").document(device_id).get()
    moods_by_date = moods_doc.to_dict() if moods_doc.exists else {}
    if moods_by_date is None:
        moods_by_date = {}
    moods = moods_by_date.get(date, [])

    if not moods:
        return jsonify({"error": "No moods for this date"}), 404

    mood_entries = "\n".join(
        f"{datetime.fromtimestamp(m['timestamp'] / 1000).strftime('%H:%M')} {m['label']}: {m['note']}"
        for m in moods
    )
    selected_prompt = random.choice(PROMPTS).format(mood_entries=mood_entries)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(selected_prompt)
        summary = response.text
    except Exception as e:
        print("Error from Gemini:", e)
        summary = "Failed to generate summary."

    # Save diary to Firestore (cloud)
    diary_ref = db.collection("user_diaries").document(device_id)
    diary_ref.set({date: {"summary": summary, "moods": moods}}, merge=True)

    # Also return the diary so the client can store it locally
    return jsonify({
        "summary": summary,
        "moods": moods,
        "date": date,
        "device_id": device_id,
        "status": "saved_to_cloud_and_returned_for_local"
    })

def send_push_notification(title, body):
    tokens_ref = db.collection("push_tokens")
    docs = tokens_ref.stream()

    messages = []
    for doc in docs:
        data = doc.to_dict()
        token = data.get("token")
        if token:
            messages.append({
                "to": token,
                "sound": "default",
                "title": title,
                "body": body,
                "data": {"targetTab": "MoodSelection"}
            })

    for i in range(0, len(messages), 100):
        chunk = messages[i:i + 100]
        response = requests.post(
            "https://exp.host/--/api/v2/push/send",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=chunk
        )
        print(f"Sent chunk {i // 100 + 1}: {response.status_code}, {response.text}")

@app.route("/api/send_notifications", methods=["POST"])
def manual_notification():
    try:
        data = request.get_json()
        title = data.get("title", "Mood check! 🕵️‍♂️")
        body = data.get("body", "How are you feeling today?")
        send_push_notification(title, body)
        return jsonify({"status": "notifications sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def schedule_notifications():
    # Convert current UTC time to Indian time
    india_tz = pytz.timezone("Asia/Kolkata")
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    now_india = now_utc.astimezone(india_tz)

    # Use Indian time for notification logic
    if dt_time(9, 0) <= now_india.time() <= dt_time(22, 0):
        title = random.choice(NOTIFICATION_TITLES)
        body = random.choice(NOTIFICATION_BODIES)
        print(f"Scheduled notification triggered (IST {now_india.strftime('%H:%M')}) with: {title} - {body}")
        send_push_notification(title, body)


scheduler = BackgroundScheduler()
for hour in [9, 12, 15, 18, 21]:
    scheduler.add_job(schedule_notifications, 'cron', hour=hour, minute=24)

scheduler.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

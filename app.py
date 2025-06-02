import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# List of prompts
PROMPTS = [
    """
Given the following list of time-stamped mood entries with short notes, write a warm, story-like mood diary for the user.
Walk through the user’s emotional journey, narrating how they felt at each point in time.
Make the tone gentle and uplifting. Include a few poetic or metaphorical lines to enhance emotional depth.
Give thoughtful advice or encouragement based on the emotional patterns.
End the response with a new line that says:
"Overall, today you were [MOOD]" — where [MOOD] is selected from this list only (exact spelling):
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Mood entries:
{mood_entries}
""",
    """
Pretend you're the user’s emotional companion.
Create a comforting mood diary from these time-stamped emotions and notes.
Describe how the user felt throughout the day using narrative and emotion-aware language.
Insert short poetic reflections or metaphors where appropriate.
Offer one piece of kind, supportive advice based on the overall trend of their feelings.
Then, finish your message with:
"Overall, today you were [MOOD]" — selected from:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Entries:
{mood_entries}
""",
    """
Take the following mood diary entries with time, emotion, and a brief note.
Turn them into a soft, poetic narrative of the user's emotional day.
Your goal is to uplift and reflect.
Use light verse or poetic lines (but not rhyme-heavy), and create a story around the user's changing moods.
End with a line of comforting advice or hope.
Finally, conclude with this sentence on a new line:
"Overall, today you were [MOOD]"

Choose the [MOOD] from:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Entries:
{mood_entries}
""",
    """
Use the following entries (which include timestamp, mood, and a brief note) to write a creative summary of the user’s day.
Present it as a flowing emotional narrative, tracing the user's journey through different moods.
Include metaphorical or poetic expressions where fitting.
Share one helpful tip or uplifting message for tomorrow.
Then on a new final line, output:
"Overall, today you were [MOOD]" — choosing one from:
Happy, Relaxed, Cheerful, Motivated, Sleepy, Anxious, Sad, Crying, Frustrated, Angry, Neutral, Hopeful, Disappoint, Grateful, Confused, Calm, Excited, Thoughtful

Diary entries:
{mood_entries}
"""
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
    if not moods:
        return jsonify({"error": "No moods provided"}), 400

    # Format the mood entries
    mood_entries = "\n".join(
        f"{datetime.fromtimestamp(m['timestamp'] / 1000).strftime('%H:%M')} {m['label']}: {m['note']}"
        for m in moods
    )

    # Choose a prompt randomly
    selected_prompt = random.choice(PROMPTS).format(mood_entries=mood_entries)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(selected_prompt)
        print("Gemini response:", response.text)
        return jsonify({"summary": response.text})
    except Exception as e:
        print("Error from Gemini:", e)
        return jsonify({"error": "Failed to generate summary"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

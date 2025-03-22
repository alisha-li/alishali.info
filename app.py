from flask import Flask, jsonify, render_template_string, render_template
import requests
import pandas as pd
from plotly_calplot import calplot
import plotly.io as pio
import os
import json
app = Flask(__name__)

@app.route("/")
def home():
    return render_template('index.html')

@app.route('/anki-stats', methods=['GET'])
def get_anki_stats():
    # Make a request to AnkiConnect to get stats
    response = requests.post('http://localhost:8765', json={
        "action": "deckNames",
        "version": 6
    })
    data = response.json()
    return jsonify(data)

def get_reviews_by_day():
    url = "http://localhost:8765"  # AnkiConnect API endpoint
    payload = {
        "action": "getNumCardsReviewedByDay",
        "version": 6
    }
    response = requests.post(url, json=payload)

    # Handle errors
    try:
        response = requests.post(url, json=payload, timeout=1)  # Set 1-second timeout
        response.raise_for_status()  # Raise error if response is bad
        data = response.json()
        if data["error"]:
            raise Exception(f"AnkiConnect error: {data['error']}")
        return data["result"]
    except Exception as e:
        print("AnkiConnect query failed:", e)
        return []

def get_reviews_by_day_cached():
    """
    Tries to fetch live data from AnkiConnect.
    If that fails, loads from the cached JSON file (anki_data.json).
    If neither works, returns an empty list.
    """
    try:
        # Try live data first
        data = get_reviews_by_day()
        with open("anki_data.json", "w") as f:
            json.dump(data, f)
        return data
    except Exception as e:
        print("Live query failed, loading cached data:", e)
        try:
            with open("anki_data.json", "r") as f:
                data = json.load(f)
            return data
        except Exception as e2:
            print("No cached data available:", e2)
            return []

def clean_review_data(data):
    """
    Clean up and fix anomalies in the review data.

    Args:
        data (list): List of [date, review_count] pairs.

    Returns:
        list: Cleaned data.
    """
    cleaned_data = []

    for date, count in data:
        # Correct specific known issues
        if date == "2024-10-17" and count > 1000:
            print(f"Fixing data for {date}: Changing {count} to 196")
            count = 196

        cleaned_data.append([date, count])

    return cleaned_data

def process_reviews_by_day(data):
    # Convert list of lists into a DataFrame
    df = pd.DataFrame(data, columns=["date", "value"])

    # Ensure the 'date' column is in datetime format
    df["date"] = pd.to_datetime(df["date"])

    return df

# Flask route to serve review data as JSON
@app.route("/api/review-data")
def review_data():
    data = get_reviews_by_day()
    return jsonify(data)

# Flask route to generate and serve the heatmap
@app.route("/anki-heatmap")
def heatmap():
    raw_data = get_reviews_by_day_cached()
    cleaned_data = clean_review_data(raw_data)  # Clean the data

    # Convert to DataFrame
    df = pd.DataFrame(cleaned_data, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    
    # Updated custom color scale
    anki_blues = [
        [0.0, "rgb(220, 240, 255)"],  # Very light neon blue
        [0.25, "rgb(120, 180, 255)"], # Light neon blue
        [0.5, "rgb(60, 120, 255)"],   # Medium neon blue
        [1.0, "rgb(0, 80, 255)"],     # Dark neon
    ]

    
    # Generate the heatmap
    fig = calplot(df, x="date", y="value", name="Reviews", colorscale=anki_blues, gap=1, years_title=True)
    html = pio.to_html(fig, full_html=False)
    html_with_header = f"""
    <div style="position: absolute; top: 10px; left: 10px;">
        <a href="/" style="text-decoration: none; font-size: 16px;"> Home </a>> Anki
    </div>
    <div style="margin-top: 50px; text-align: center; font-size: 20px; font-family: Arial;">
        <a href="https://apps.ankiweb.net/" target="_blank">Anki</a> is a spaced repetition flashcard software. Below is a heatmap of my reviews.
    </div>
    <br><br>
    {html}
    """
    return render_template_string(html_with_header)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Defaults to 5000 if PORT isn't set
    app.run(host="0.0.0.0", port=port)
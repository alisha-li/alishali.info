import requests
import json
from datetime import datetime

def get_reviews_by_day():
    url = "http://localhost:8765"
    payload = {
        "action": "getNumCardsReviewedByDay",
        "version": 6
    }
    response = requests.post(url, json=payload)
    result = response.json()
    if result.get("error"):
        raise Exception(f"AnkiConnect error: {result['error']}")
    return result["result"]

def update_data():
    try:
        data = get_reviews_by_day()
        with open("anki_data.json", "w") as f:
            json.dump(data, f)
        print(f"Anki data updated successfully at {datetime.now()}")
    except Exception as e:
        print("Error updating Anki data:", e)

if __name__ == "__main__":
    update_data()

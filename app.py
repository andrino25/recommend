from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from collections import Counter
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()

# Firebase configuration from environment variables
firebase_config = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL")
}

# Initialize Firebase app
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_config["databaseURL"]
})

# Mock user click history for testing
user_clicks = {
    "user_123": ["Cooking", "Gardening", "Grocery Shopping", "Cooking", "Cooking"],
    "user_456": ["cooking", "school_work", "grocery_shopping"],
}

class ClickData(BaseModel):
    user_id: str
    clicked_category: str

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Recommendation API with Firebase!"}

@app.post("/update-clicks")
async def update_clicks(click_data: ClickData):
    user_id = click_data.user_id
    clicked_category = click_data.clicked_category

    print(f"Received click from user: {user_id}, category: {clicked_category}")

    if user_id not in user_clicks:
        user_clicks[user_id] = []

    user_clicks[user_id].append(clicked_category)

    print(f"Updated click history for the {user_id}: {user_clicks[user_id]}")

    return {"status": "success", "message": f"Click recorded for {clicked_category}"}

@app.get("/get-recommendations/{user_id}")
async def get_recommendations(user_id: str, window_size: int = 5):
    if user_id not in user_clicks:
        return {"status": "error", "message": "User not found"}

    user_click_history = user_clicks[user_id]
    recent_clicks = user_click_history[-window_size:]

    category_counts = Counter(recent_clicks)
    most_common_categories = category_counts.most_common(3)

    recommendations = {}
    for category, _ in most_common_categories:
        # Retrieve category and subcategory recommendations from Firebase
        category_ref = db.reference(f"category/{category}/SubCategories")
        category_data = category_ref.get()

        if category_data:
            recommendations[category] = [sub["name"] for sub in category_data.values()]

    return {
        "status": "success",
        "most_common_categories": [category for category, _ in most_common_categories],
        "recommendations": recommendations,
        "recent_clicks": recent_clicks
    }

@app.delete("/reset-clicks/{user_id}")
async def reset_clicks(user_id: str):
    if user_id in user_clicks:
        del user_clicks[user_id]  # Remove the user's click history
        return {"status": "success", "message": f"Click history for {user_id} has been reset."}
    else:
        raise HTTPException(status_code=404, detail="User not found")

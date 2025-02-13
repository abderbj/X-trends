from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set secret key
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key")

# Get API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("No GEMINI_API_KEY found in environment variables.")

# Construct API URL
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Define headers for API requests
HEADERS = {"Content-Type": "application/json"}

import time
import requests

def generate_response(prompt_text, max_retries=5):
    """
    Sends user input to the Gemini API with rate limiting and retries.
    """
    data = {"contents": [{"role": "user", "parts": [{"text": prompt_text}]}]}
    
    attempt = 0
    wait_time = 2  # Start with a 2-second delay

    while attempt < max_retries:
        try:
            response = requests.post(GEMINI_API_URL, headers=HEADERS, json=data)
            
            # If the response is successful, return the result
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "No response from AI.")
            
            # If too many requests, wait and retry
            elif response.status_code == 429:
                print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                wait_time *= 2  # Exponential backoff
                
            else:
                response.raise_for_status()  # Raise other HTTP errors
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return f"Request error: {str(e)}"
        
        attempt += 1

    return "Failed to get a response after multiple attempts."


@app.route("/analyze", methods=["POST"])
def analyze_posts():
    """
    Extracts posts and user interests from the request, analyzes them,
    and returns relevant trending posts filtered by interest.
    """
    data = request.json
    
    posts = data.get("posts", [])  # List of posts
    interests = set(data.get("interests", []))  # Convert interests to a set for quick lookup
    
    if not posts:
        return jsonify({"error": "No posts provided"}), 400

    analyzed_posts = []

    for post in posts:
        results = {}

        # Perform 3 iterations before processing the full analysis
        for i in range(3):
            print(f"Iteration {i+1} for post: {post}")
            time.sleep(1)  # Pause for 1 second

        prompts = {
            "category": f"What is the general category of this post? Respond in one word exactly.\n{post}",
            "language": f"What language is this post written in? Respond in one word exactly.\n{post}",
            "hashtags": f"Generate relevant hashtags for this post. (Separate them with a comma)\n{post}",
            "topic": f"Summarize the main topic of this post. (Straight to the point)\n{post}",
            "trending_posts": f"Generate 3 new posts based on the same topic that could go viral. (Just the three new posts in the same language and separate them by a comma) \n{post}"
        }

        for key, prompt in prompts.items():
            response = generate_response(prompt).strip()

            # If the key is 'trending_posts' or 'hashtags', split it into an array
            if key in ["trending_posts", "hashtags"]:
                results[key] = [item.strip() for item in response.split(",")]
            else:
                results[key] = response

        # Store results in analyzed_posts list
        analyzed_posts.append(results)

    # Filter posts that match the user's interests
    filtered_posts = [
        post for post in analyzed_posts if any(interest.lower() in post["category"].lower() for interest in interests)
    ]

    return jsonify({"filtered_posts": filtered_posts})

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)

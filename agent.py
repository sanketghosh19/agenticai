import requests
from googlesearch import search
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import logging
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)

# --- Step 1: Define Job Criteria & Google Dork Query ---
job_description = """
Looking for a Python Developer in India with strong skills in software development.
"""
google_query = 'site:linkedin.com/in/ "Python Developer" "India" -jobs -careers'

# --- Step 2: Search using Google Dorking and extract LinkedIn usernames ---
def extract_linkedin_usernames(query, num_results=5):
    usernames = []
    logging.info("Searching Google with query: %s", query)
    for url in search(query, num_results=num_results, lang="en"):
        parsed_url = urlparse(url)
        # Check if the URL contains '/in/'
        if "linkedin.com/in/" in url:
            # Split the path and filter out empty strings
            parts = [p for p in parsed_url.path.strip("/").split("/") if p]
            # We expect the first part to be "in" and the second part to be the username
            if parts and parts[0].lower() == "in" and len(parts) >= 2:
                username = parts[1]
                if username and username not in usernames:
                    usernames.append(username)
            else:
                logging.debug("URL did not have the expected structure: %s", url)
    return usernames

usernames = extract_linkedin_usernames(google_query, num_results=5)
logging.info("Extracted LinkedIn usernames: %s", usernames)

# --- Step 3: Retrieve LinkedIn profile details from RapidAPI ---
rapidapi_url = "https://linkedin-api8.p.rapidapi.com/"
rapidapi_headers = {
    "x-rapidapi-key": "ce90f77b98msh21b88e114f61f4ep1c3419jsn3f83c3babe93",  # Use your actual key
    "x-rapidapi-host": "linkedin-api8.p.rapidapi.com"
}

def get_linkedin_profile(username):
    querystring = {"username": username}
    logging.info("Fetching profile for username: %s", username)
    response = requests.get(rapidapi_url, headers=rapidapi_headers, params=querystring)
    if response.status_code == 200:
        return response.json()  # assuming API returns JSON profile data
    else:
        logging.warning("Failed to get profile for %s, status code: %s", username, response.status_code)
        return None

profiles_data = []
for username in usernames:
    profile_json = get_linkedin_profile(username)
    if profile_json:
        # Combine several fields to form a profile text; adjust keys based on API response
        profile_text = f"{profile_json.get('name', '')}\n{profile_json.get('headline', '')}\n{profile_json.get('summary', '')}"
        profiles_data.append({
            "username": username,
            "profile_text": profile_text,
            "source_url": f"https://www.linkedin.com/in/{username}"
        })

logging.info("Fetched profile details for %d users.", len(profiles_data))

# --- Step 4: Generate Embeddings for Each Profile ---
model = SentenceTransformer('all-MiniLM-L6-v2')
for profile in profiles_data:
    profile_text = profile["profile_text"]
    profile["embedding"] = model.encode(profile_text).tolist()  # Convert numpy array to list

# --- Step 5: Setup ChromaDB for Storing Profile Embeddings ---
chroma_client = chromadb.Client()  # Default initialization; adjust Settings if needed.
collection_name = "linkedin_profiles"
if collection_name in chroma_client.list_collections():
    collection = chroma_client.get_collection(name=collection_name)
else:
    collection = chroma_client.create_collection(name=collection_name)

# Insert profiles into the collection
for profile in profiles_data:
    collection.add(
        documents=[profile["profile_text"]],
        metadatas=[{"source_url": profile["source_url"], "username": profile["username"]}],
        ids=[f"profile_{hash(profile['profile_text'])}"],
        embeddings=[profile["embedding"]]
    )

logging.info("Profiles stored in ChromaDB successfully.")

# --- Example Query: Find profiles matching a query ---
query_result = collection.query(
    query_texts=["Python Developer in India"],  # Example query text
    n_results=2,
)
print("Query Result:", query_result)

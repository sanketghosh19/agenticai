import os
import requests
import logging
import pandas as pd
from urllib.parse import urlparse
from googlesearch import search
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

# --- Step 1: Define Job Criteria & Google Dork Query ---
job_description = """
Looking for a Python Developer in India with strong skills in software development.
"""
google_query = 'site:linkedin.com/in/ "Python Developer" "India" -jobs -careers'

# --- Step 2: Search using Google Dorking and extract LinkedIn usernames ---
def extract_linkedin_usernames(query, num_results=15):
    usernames = []
    logging.info("Searching Google with query: %s", query)
    for url in search(query, num_results=num_results, lang="en"):
        parsed_url = urlparse(url)
        # Check if the URL contains '/in/'
        if "linkedin.com/in/" in url:
            parts = [p for p in parsed_url.path.strip("/").split("/") if p]
            # Expect first part to be "in" and the second part to be the username
            if parts and parts[0].lower() == "in" and len(parts) >= 2:
                username = parts[1]
                if username and username not in usernames:
                    usernames.append(username)
            else:
                logging.debug("URL did not have the expected structure: %s", url)
    return usernames

usernames = extract_linkedin_usernames(google_query, num_results=15)
logging.info("Extracted LinkedIn usernames: %s", usernames)

# --- Step 3: Retrieve LinkedIn profile details from RapidAPI ---
rapidapi_url = "https://linkedin-api8.p.rapidapi.com/"
rapidapi_headers = {
    "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY"),
    "x-rapidapi-host": os.environ.get("RAPIDAPI_HOST")
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

profiles = []
for username in usernames:
    profile_json = get_linkedin_profile(username)
    if profile_json:
        # Flatten the profile JSON into a dictionary for Excel
        profile_data = {}
        profile_data["id"] = profile_json.get("id", "")
        profile_data["urn"] = profile_json.get("urn", "")
        profile_data["username"] = username
        profile_data["firstName"] = profile_json.get("firstName", "")
        profile_data["lastName"] = profile_json.get("lastName", "")
        profile_data["headline"] = profile_json.get("headline", "")
        profile_data["summary"] = profile_json.get("summary", "")
        
        # Extract Experience from 'position' and 'fullPositions'
        positions = profile_json.get("position", [])
        full_positions = profile_json.get("fullPositions", [])
        all_positions = positions + full_positions
        unique_positions = []
        seen = set()
        for pos in all_positions:
            pos_key = (pos.get("title", ""), pos.get("companyName", ""))
            if pos_key not in seen:
                seen.add(pos_key)
                unique_positions.append(pos)
        experience = "\n".join([f"{pos.get('title', '')} at {pos.get('companyName', '')}" for pos in unique_positions])
        profile_data["Experience"] = experience
        
        # Extract Skills
        skills_list = profile_json.get("skills", [])
        skills = ", ".join([skill.get("name", "") for skill in skills_list])
        profile_data["Skills"] = skills
        
        # Extract Education details
        educations = profile_json.get("educations", [])
        education_str = "\n".join([
            f"{edu.get('degree', '')} in {edu.get('fieldOfStudy', '')} from {edu.get('schoolName', '')}"
            for edu in educations
        ])
        profile_data["Education"] = education_str
        
        # Additional sections from the profile can be added here as needed
        
        profiles.append(profile_data)

logging.info("Fetched profile details for %d users.", len(profiles))

# --- Step 4: Save the profile details to an Excel file ---
df = pd.DataFrame(profiles)
excel_file = "linkedin_profiles.xlsx"
df.to_excel(excel_file, index=False)
logging.info("Saved profile details to %s", excel_file)
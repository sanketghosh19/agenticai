import requests

url = "https://linkedin-data-api.p.rapidapi.com"

querystring = {"username":"prajna-shetty-772938146"}

headers = {
    'x-rapidapi-key': "ce90f77b98msh21b88e114f61f4ep1c3419jsn3f83c3babe93",
    'x-rapidapi-host': "linkedin-data-api.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())
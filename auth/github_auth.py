import os
import jwt
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_APP_ID=os.getenv("GITHUB_APP_ID")
GITHUB_PRIVATE_KEY=os.getenv("GITHUB_PRIVATE_KEY")
GITHUB_INSTALLATION_ID=os.getenv("GITHUB_INSTALLATION_ID")

if not(GITHUB_APP_ID and GITHUB_PRIVATE_KEY and GITHUB_INSTALLATION_ID):
    raise Exception(f"""Missing required environment variables:
    APP_ID: ${GITHUB_APP_ID}
    PRIVATE_KEY: ${GITHUB_PRIVATE_KEY}
    INSTALLATION_ID: ${GITHUB_INSTALLATION_ID}""" )


def generate_jwt():
    with open("private_key.pem", "r") as f:
        private_key = f.read()

    payload = {
        "iat": int(time.time()),  # Issued at time
        "exp": int(time.time()) + 60,  # Expires in 10 minutes
        "iss": GITHUB_APP_ID,  # GitHub App ID
    }

    return jwt.encode(payload, private_key, algorithm="RS256")



def generate_installation_token():
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    }

    token_url = f"https://api.github.com/app/installations/{GITHUB_INSTALLATION_ID}/access_tokens"
    token_response = requests.post(token_url, headers=headers)
    token_response.raise_for_status()

    installation_token = token_response.json()["token"]
    
    return installation_token
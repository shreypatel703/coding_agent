import jwt
import time
import requests

def generate_jwt(app_id, insallation_id):
    with open("private_key.pem", "r") as f:
        private_key = f.read()

    payload = {
        "iat": int(time.time()),  # Issued at time
        "exp": int(time.time()) + 600,  # Expires in 10 minutes
        "iss": app_id,  # GitHub App ID
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


def generate_installation_token(app_id, installation_id):
    jwt_token = generate_jwt(app_id, installation_id)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    }

    token_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    token_response = requests.post(token_url, headers=headers)
    token_response.raise_for_status()

    installation_token = token_response.json()["token"]
    
    return installation_token
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise Exception("Missing OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_text(prompt: str):
    # Make an API call to OpenAI to generate text
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )
    response_message = response.choices[0].message.content
    return response_message

def generate_json(prompt: str):
    # Make an API call to OpenAI to generate text
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4-turbo",
        response_format={ "type": "json_object" }
    )
    response_message = response.choices[0].message.content
    
    return response_message
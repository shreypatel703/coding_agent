import json
from flask import Flask, request, jsonify
from webhook.webhook_handler import process_webhook

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Hello World"


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

    try:
        event = request.headers.get("X-GitHub-Event")
        return process_webhook(event, data)
    except Exception as error:
        print("Error processing webhook:", error)
        return jsonify({"message": "Internal Server Error"}), 500
    

if __name__ == '__main__':
    app.run(port=5000)
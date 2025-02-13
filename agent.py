from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os






app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Hello World"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json  # Get JSON payload
    print("Received Webhook Data:", data)
    return jsonify({"message": "Webhook received!"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)


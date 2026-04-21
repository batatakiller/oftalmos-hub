import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

EVO_URL = os.getenv("EVO_URL")
EVO_KEY = os.getenv("EVO_KEY")
EVO_INSTANCE = os.getenv("EVO_INSTANCE")

def check_webhook():
    url = f"{EVO_URL}/webhook/find/{EVO_INSTANCE}"
    headers = {"apikey": EVO_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("Webhook current config:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error checking webhook: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting: {e}")

if __name__ == "__main__":
    check_webhook()

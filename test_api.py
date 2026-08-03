import base64
import json
import urllib.request

API_URL = "https://ht0np47e31.execute-api.us-east-1.amazonaws.com/default/whisper-transcribe-dev"
AUDIO_FILE = r"test-ai-model.mp3"

with open(AUDIO_FILE, "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

body = json.dumps({"audio_base64": audio_b64}).encode("utf-8")
req = urllib.request.Request(API_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2))

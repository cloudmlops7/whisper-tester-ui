import base64
import json
import logging
import time

import requests
from flask import Flask, render_template, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    api_url = request.form.get("api_url", "").strip()
    audio_file = request.files.get("audio_file")

    if not api_url:
        return jsonify({"error": "API Gateway URL is required"}), 400
    if not audio_file:
        return jsonify({"error": "Audio file is required"}), 400

    audio_bytes = audio_file.read()
    if len(audio_bytes) == 0:
        return jsonify({"error": "Uploaded file is empty"}), 400

    log.info("File: %s | Size: %.2f KB", audio_file.filename, len(audio_bytes) / 1024)

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {"audio_base64": audio_b64}

    log.info("Forwarding to: %s | Payload size: %.2f KB", api_url, len(json.dumps(payload)) / 1024)

    try:
        t_start = time.perf_counter()
        resp = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=(10, 300),  # (connect timeout, read timeout)
        )
        latency_ms = round((time.perf_counter() - t_start) * 1000)

        log.info("Lambda response status: %d | Latency: %d ms", resp.status_code, latency_ms)
        log.info("Lambda response body: %s", resp.text[:500])

        if resp.status_code != 200:
            return jsonify({"error": f"HTTP {resp.status_code}: {resp.text}"}), 502

        result = resp.json()

        # Unwrap API Gateway proxy envelope if present
        if "body" in result:
            body = result["body"]
            result = json.loads(body) if isinstance(body, str) else body

        return jsonify({"success": True, "data": result, "latency_ms": latency_ms})

    except requests.exceptions.Timeout:
        log.error("Request timed out")
        return jsonify({"error": "Request timed out — Lambda took too long to respond"}), 504
    except requests.exceptions.ConnectionError as e:
        log.error("Connection error: %s", e)
        return jsonify({"error": f"Could not reach API: {e}"}), 502
    except Exception as e:
        log.error("Unexpected error: %s", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

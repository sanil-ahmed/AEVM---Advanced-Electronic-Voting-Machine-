# backend/fingerprint_api.py
"""
Fingerprint enrollment API (separate service).
Run this only when you want to enroll fingerprints (demo/registration).
It updates the existing voters table (adds fingerprint_id or fingerprint_template).
"""

from flask import Flask, request, jsonify
import os
import db  # assumes you run this file from the backend/ directory
import base64

app = Flask(__name__)

# Simple shared secret to avoid accidental/public writes (change before use)
ADMIN_KEY = os.environ.get("FP_ADMIN_KEY", "changeme123")

# -------------------------
# 1) Save a sensor-assigned ID (simplest)
# -------------------------
@app.route("/register_fingerprint_id", methods=["POST"])
def register_fingerprint_id():
    """
    JSON: { "nid": "12345", "finger_id": 12, "admin_key": "..." }
    This stores a simple integer id (finger_id) in voters.fingerprint_id.
    Works if the sensor keeps templates internally and assigns IDs.
    """
    data = request.get_json(force=True)
    nid = data.get("nid")
    finger_id = data.get("finger_id")
    key = data.get("admin_key", "")

    if key != ADMIN_KEY:
        return jsonify({"status": "error", "message": "unauthorized"}), 401
    if not nid or finger_id is None:
        return jsonify({"status": "error", "message": "nid and finger_id required"}), 400

    conn = db.create_connection()
    if not conn:
        return jsonify({"status":"error","message":"DB connection failed"}), 500
    cur = conn.cursor()
    cur.execute("SELECT NID FROM voters WHERE NID = ?", (nid,))
    if not cur.fetchone():
        conn.close()
        return jsonify({"status":"error","message":"NID not found"}), 404

    cur.execute("UPDATE voters SET fingerprint_id = ? WHERE NID = ?", (finger_id, nid))
    conn.commit()
    conn.close()
    return jsonify({"status":"ok", "message":"finger_id stored", "nid": nid, "finger_id": finger_id})


# -------------------------
# 2) Save a raw template (hex/base64) — advanced
# -------------------------
@app.route("/upload_fingerprint_template", methods=["POST"])
def upload_fingerprint_template():
    """
    JSON: { "nid":"12345", "template":"<BASE64_OR_HEX_STRING>", "format": "base64"|"hex", "admin_key":"..." }
    Stores a template string into voters.fingerprint_template (TEXT/BLOB).
    """
    data = request.get_json(force=True)
    nid = data.get("nid")
    template = data.get("template")
    fmt = data.get("format", "base64")
    key = data.get("admin_key", "")

    if key != ADMIN_KEY:
        return jsonify({"status": "error", "message": "unauthorized"}), 401
    if not nid or not template:
        return jsonify({"status": "error", "message": "nid and template required"}), 400
    if fmt not in ("base64", "hex"):
        return jsonify({"status": "error", "message": "format must be 'base64' or 'hex'"}), 400

    # Optional: verify the nid exists
    conn = db.create_connection()
    if not conn:
        return jsonify({"status":"error","message":"DB connection failed"}), 500
    cur = conn.cursor()
    cur.execute("SELECT NID FROM voters WHERE NID = ?", (nid,))
    if not cur.fetchone():
        conn.close()
        return jsonify({"status":"error","message":"NID not found"}), 404

    # store template as TEXT (you can store as BLOB if you prefer)
    cur.execute("UPDATE voters SET fingerprint_template = ? WHERE NID = ?", (template, nid))
    conn.commit()
    conn.close()

    return jsonify({"status":"ok", "message":"template stored", "nid": nid, "format": fmt})


# small health endpoint
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status":"ok", "message":"fingerprint_api alive"})


if __name__ == "__main__":
    print("Fingerprint enrollment API starting (use this only for enrollment).")
    print("Change ADMIN_KEY env var before real use. Example: set FP_ADMIN_KEY=MySecretKey")
    app.run(host="0.0.0.0", port=5000, debug=True)

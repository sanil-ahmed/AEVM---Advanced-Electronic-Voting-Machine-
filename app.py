import db
import face_utils
import numpy as np
import cv2
from datetime import datetime
from flask import Flask, jsonify, request
import time

app = Flask(__name__)

VOTING_STATE = {
    "current_page": "welcome",
    "current_nid": None,
    "voter_name": None,
    "voter_photo_path": None,
    "nid_input": "",
    "status_message": "Please Enter Your NID on the Keypad"
}

try:
    face_utils.load_all_voter_encodings()
except Exception as e:
    print(f"Warning: Could not load face encodings: {e}")


@app.route('/')
def home():
    return "Backend Server is Running!"


@app.route('/get_status', methods=['GET'])
def get_status():
    return jsonify(VOTING_STATE)


@app.route('/reset_state', methods=['POST'])
def reset_state():
    VOTING_STATE.update({
        "current_page": "welcome",
        "current_nid": None,
        "voter_name": None,
        "voter_photo_path": None,
        "nid_input": "",
        "status_message": "Please Enter Your NID on the Keypad"
    })
    print("State reset to welcome.")
    return jsonify({"status": "success"})


@app.route('/key_press', methods=['POST'])
def key_press_route():
    key = request.json.get('key')
    if VOTING_STATE.get("current_page") == "welcome":
        if key == '*':
            VOTING_STATE["nid_input"] = VOTING_STATE.get("nid_input", "")[:-1]
        elif key != '#':
            VOTING_STATE["nid_input"] = VOTING_STATE.get("nid_input", "") + key

        if VOTING_STATE["nid_input"]:
            VOTING_STATE["status_message"] = f"NID: {VOTING_STATE['nid_input']}"
        else:
            VOTING_STATE["status_message"] = "Please Enter Your NID on the Keypad"

    return jsonify({"status": "ok"})


@app.route('/candidates', methods=['GET'])
def get_candidates_route():
    candidates = [dict(row) for row in db.get_all_candidates()]
    return jsonify({"status": "success", "candidates": candidates})


@app.route('/verify_nid', methods=['POST'])
def verify_nid_route():
    nid = request.json.get('nid', "").strip()
    voter = db.get_voter_by_nid(nid)

    if not voter:
        VOTING_STATE["status_message"] = f"NID {nid} not found. Please try again."
        return jsonify({"status": "error", "message": "NID not found"}), 404

    if voter['is_voted']:
        VOTING_STATE["status_message"] = f"Voter {nid} has already voted."
        return jsonify({"status": "error", "message": "Voter already voted"}), 403

    VOTING_STATE.update({
        "current_page": "fingerprint",
        "current_nid": nid,
        "voter_name": voter['Name'],
        "voter_photo_path": voter['face_photo'],
        "status_message": "NID Verified. Please place your finger on the sensor."
    })
    return jsonify({"status": "success", "voter_name": voter['Name']})


@app.route('/verify_fingerprint', methods=['POST'])
def verify_fingerprint_route():
    nid = request.json.get('nid', "").strip()
    finger_id = request.json.get('finger_id')
    voter = db.get_voter_by_nid(nid)

    if str(voter['fingerprint_template']) == str(finger_id):
        db.update_voter_attempts(nid, 0)
        VOTING_STATE["current_page"] = "candidates"
        VOTING_STATE["status_message"] = "Fingerprint Matched. Please select your candidate."
        return jsonify({"status": "match"})
    else:
        attempts = voter['fingerprint_attempts'] + 1
        db.update_voter_attempts(nid, attempts)
        if attempts >= 3:
            VOTING_STATE["current_page"] = "face"
            VOTING_STATE["status_message"] = "Fingerprint failed. Press YES button to verify with face."
            return jsonify({"status": "fail_max_attempts"})
        else:
            VOTING_STATE["status_message"] = f"Finger did not Match. Please Try Again. ({3 - attempts} tries left)"
            return jsonify({"status": "fail_try_again"})


@app.route('/verify_face', methods=['POST'])
def verify_face_route():
    nid = VOTING_STATE.get("current_nid")
    if not nid:
        return jsonify({"status": "error", "message": "No NID in session."}), 400

    VOTING_STATE["status_message"] = "Verifying... Please wait."
    print("Received face verify trigger. Waiting for GUI to release camera...")
    time.sleep(1.5)
    print(f"Attempting face capture for NID: {nid}...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam on server side.")
        VOTING_STATE["status_message"] = "Error: Could not access camera."
        return jsonify({"status": "error", "message": "Could not open webcam."}), 500

    # --- FIX: CAMERA WARM-UP ---
    print("Camera opened by server. Warming up sensor...")
    for i in range(10):
        warmup_ret, _ = cap.read()
        if not warmup_ret:
            print(f"Error: Failed to read frame {i} during warmup.")
            cap.release()
            VOTING_STATE["status_message"] = "Error: Camera sensor failed."
            return jsonify({"status": "error", "message": "Failed to warm up camera."}), 500

    print("Warmup complete. Capturing final verification frame...")
    # --- END OF FIX ---

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Failed to capture frame from webcam.")
        VOTING_STATE["status_message"] = "Error: Could not capture image."
        return jsonify({"status": "error", "message": "Failed to capture image."}), 500

    matched_nid = face_utils.compare_and_verify(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    if matched_nid and matched_nid == nid:
        VOTING_STATE["current_page"] = "candidates"
        VOTING_STATE["status_message"] = "Face Matched. Please select candidate."
        print(f"Face match SUCCESS for NID: {matched_nid}")
        return jsonify({"status": "match"})
    else:
        VOTING_STATE["current_page"] = "welcome"
        VOTING_STATE["status_message"] = "Face verification failed. Please try again from start."
        print(f"Face match FAILED. Found: '{matched_nid}', Expected: '{nid}'.")
        return jsonify({"status": "no_match"})


@app.route('/cast_vote', methods=['POST'])
def cast_vote_route():
    nid = request.json.get('nid', "").strip()
    candidate_id = request.json.get('candidate_id')

    if VOTING_STATE.get("current_nid") != nid or VOTING_STATE.get("current_page") != "candidates":
        return jsonify({"status": "error", "message": "Invalid state for voting."}), 400

    if db.log_vote(candidate_id, nid):
        VOTING_STATE["current_page"] = "voted"
        VOTING_STATE["status_message"] = "Your Vote is Confirmed! Thank you."
        return jsonify({"status": "success"})
    else:
        VOTING_STATE["current_page"] = "welcome"
        VOTING_STATE["status_message"] = "Voting failed. Voter may have already voted."
        return jsonify({"status": "error", "message": "Vote logging failed."}), 500


if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True)


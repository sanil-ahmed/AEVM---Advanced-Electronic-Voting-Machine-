import requests
import json
import db  # Assuming db.py is available for direct verification if needed

# --- Configuration ---
# Use the IP address of your local machine
FLASK_SERVER_IP = "192.168.0.245"
# The main app.py runs on port 5000
VERIFY_FINGERPRINT_URL = f"http://{FLASK_SERVER_IP}:5000/verify_fingerprint"

# Data for the voter you successfully enrolled (e.g., Samson)
ENROLLED_VOTER_DATA = {
    "nid": "112330940",
    # The Sensor ID that the ESP32 found and sent (which should be '3' from your test)
    "sensor_id": 3,
    # The live_fingerprint_data field is required by the API but we only need sensor_id for now.
    "live_fingerprint_data": "SIMULATED_DATA_OK"
}

# Data for a voter who failed enrollment (e.g., someone with no template or wrong finger)
UNMATCHED_VOTER_DATA = {
    "nid": "112330940",
    "sensor_id": 99,  # Sensor ID found by ESP32 that does NOT match DB (DB has '3')
    "live_fingerprint_data": "SIMULATED_DATA_FAIL"
}


# --- Helper Functions ---

def send_verification_request(data):
    """Sends a POST request to the /verify_fingerprint API."""
    print(f"\n--- Testing NID: {data['nid']} with Sensor ID: {data['sensor_id']} ---")
    try:
        response = requests.post(
            VERIFY_FINGERPRINT_URL,
            json=data,
            headers={'Content-Type': 'application/json'}
        )

        print(f"Status Code: {response.status_code}")

        # Check if the response body is valid JSON
        try:
            response_json = response.json()
            print("API Response:")
            print(json.dumps(response_json, indent=4))
        except json.JSONDecodeError:
            print("API Response (Not JSON):", response.text)

    except requests.exceptions.RequestException as e:
        print(f"CONNECTION ERROR: {e}")
        print("-> Ensure 'app.py' is running on port 5000 and the IP is correct.")


# --- Main Test Execution ---
if __name__ == "__main__":
    print(f"Starting Fingerprint Verification Tests...")
    print(f"Target URL: {VERIFY_FINGERPRINT_URL}")

    # 1. Test case: Successful Match (Sensor ID matches DB value)
    send_verification_request(ENROLLED_VOTER_DATA)

    # 2. Test case: Unsuccessful Match (Sensor ID does NOT match DB value)
    send_verification_request(UNMATCHED_VOTER_DATA)

    print("\nTests complete. Check the status and message fields in the response.")
    print("Expected Status for successful match: 'match'")
    print("Expected Status for unsuccessful match: 'fail try again' or similar")

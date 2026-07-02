import serial
import time
import requests
import sys

# --- Configuration ---
ESP32_COM_PORT = 'COM7'
SERVER_URL = 'http://192.168.0.245:5000'


# --- Main Program ---
def enroll_voter():
    """Main function to handle the enrollment process."""
    try:
        print(f"🔹 Attempting to connect to ESP32 on {ESP32_COM_PORT}...")
        esp32 = serial.Serial(ESP32_COM_PORT, 115200, timeout=5)  # Increased timeout
        time.sleep(2)
    except serial.SerialException:
        print(f"❌ CRITICAL ERROR: Could not open port {ESP32_COM_PORT}.")
        sys.exit(1)

    # ** THIS IS THE FIX **
    # Wait for the specific "ENROLLMENT_READY" signal, ignoring boot messages
    print("   ... Waiting for enrollment firmware to be ready...")
    ready_signal = ""
    while "ENROLLMENT_READY" not in ready_signal:
        ready_signal = esp32.readline().decode('utf-8').strip()
        if not ready_signal:
            print("❌ Timed out waiting for ESP32 ready signal. Please reset the ESP32 and try again.")
            esp32.close()
            return

    print(f"✅ Successfully connected to ESP32 Enrollment Firmware.")

    while True:
        nid = input("\n> Enter the Voter NID to enroll (or type 'exit' to quit): ").strip()
        if nid.lower() == 'exit':
            break
        if not nid.isdigit():
            print("❌ Invalid NID. Please enter only numbers.")
            continue

        print(f"🔹 Starting enrollment for NID: {nid}")
        print("👉 Tell the voter to place their finger on the sensor...")

        esp32.write(b'enroll\n')

        template_hex = ""
        while True:
            line = esp32.readline().decode('utf-8').strip()
            if not line:
                continue

            if line.startswith("TEMPLATE:"):
                template_hex = line.split(":", 1)[1]
                print("✅ Received fingerprint template from sensor.")
                break
            elif line.startswith("ERROR:"):
                print(f"❌ ESP32 reported an error: {line}")
                template_hex = ""
                break
            elif line.startswith("STATUS:"):
                print(f"   ... {line.split(':', 1)[1]}")

        if template_hex:
            try:
                # NOTE: The server expects a Base64 string, but Hex is also fine for text transport.
                # We will tell the server this is a hex string.
                response = requests.post(
                    f"{SERVER_URL}/enroll_fingerprint",
                    json={"nid": nid, "template": template_hex}
                )
                if response.status_code == 200:
                    print("✅ Server successfully saved the fingerprint template!")
                else:
                    print(f"❌ Server error: {response.json().get('message', 'Unknown error')}")
            except requests.exceptions.RequestException as e:
                print(f"❌ CRITICAL ERROR: Could not connect to the server. Is it running? Details: {e}")

    esp32.close()
    print("👋 Enrollment program finished.")


if __name__ == '__main__':
    enroll_voter()


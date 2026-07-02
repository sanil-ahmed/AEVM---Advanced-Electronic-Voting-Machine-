import cv2
import face_recognition
import numpy as np

# --- Fix for Standalone Run: Directly Import DB and Face Utils ---
# We must use absolute paths because PyCharm runs this file individually.
# The code below assumes you copy the final code you developed into this file.

# Since you are running this test code *outside* of the Flask app,
# you need the database and face logic directly:
import db  # Assuming db.py is in the same directory (backend/)
import face_utils  # Assuming face_utils.py is in the same directory (backend/)

# --- Core Logic ---
# Load all encodings
print("🔄 Loading encodings from DB...")
# NOTE: Call the load function from face_utils to populate the globals
face_utils.load_all_voter_encodings()
print(f"✅ Loaded {len(face_utils.known_face_ids)} voters")

# Start webcam
video_capture = cv2.VideoCapture(0)

if not video_capture.isOpened():
    print("❌ Could not open webcam. Check camera connection.")
    exit()

print("🎥 Webcam started. Press 'q' to quit.")

while True:
    ret, frame = video_capture.read()
    if not ret:
        print("❌ Failed to grab frame")
        break

    # Convert frame to RGB for face_recognition library
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect faces
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        # Compare with DB (using the global list populated by face_utils)
        matches = face_recognition.compare_faces(face_utils.known_face_encodings, face_encoding)
        face_distances = face_recognition.face_distance(face_utils.known_face_encodings, face_encoding)

        # Check for best match
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)

            top, right, bottom, left = face_location

            # Ensure the index is valid
            if matches[best_match_index] and best_match_index < len(face_utils.known_face_names):
                nid = face_utils.known_face_ids[best_match_index]
                name = face_utils.known_face_names[best_match_index]
                label = f"{name} (NID: {nid})"
                color = (0, 255, 0)  # Green
                print(f"✅ Match found: {name} (NID: {nid})")
            else:
                label = "Unknown"
                color = (0, 0, 255)  # Red
                print("❌ Unknown face detected")

            # Draw box & label
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Show video
    cv2.imshow('Face Recognition - Press Q to quit', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()
import face_recognition
import cv2
import numpy as np
import db
import face_utils

# Load all known encodings from DB
print("Loading encodings...")
face_utils.load_all_voter_encodings()

# Pick one known image to test
test_image_path = r"E:\VotingApp_Project\images\navana.jpg"  # change path to any existing image
print(f"Testing with: {test_image_path}")

# Load test image
test_image = face_recognition.load_image_file(test_image_path)
test_encoding = face_recognition.face_encodings(test_image)[0]

# Compare with database encodings
matches = face_recognition.compare_faces(face_utils.known_face_encodings, test_encoding)
face_distances = face_recognition.face_distance(face_utils.known_face_encodings, test_encoding)

best_match_index = np.argmin(face_distances)

if matches[best_match_index]:
    nid = face_utils.known_face_ids[best_match_index]
    print(f"✅ Match found! NID: {nid}")
else:
    print("❌ No match found.")

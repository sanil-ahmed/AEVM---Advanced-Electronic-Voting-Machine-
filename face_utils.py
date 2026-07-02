import face_recognition
import os
import cv2
import db

# Globals to store loaded encodings and IDs
known_face_encodings = []
known_face_ids = []
known_face_names = []

# Get the absolute path to the main project root
# Assumes face_utils.py is in backend/, so we go up one level ("..")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_all_voter_encodings():
    """Loads all voter face encodings from the database."""
    global known_face_encodings, known_face_ids, known_face_names
    known_face_encodings.clear()
    known_face_ids.clear()
    known_face_names.clear()

    print("🔄 Loading all voter face encodings from DB...")

    voters = db.get_all_voters()
    if not voters:
        print("⚠️ No voters found in the database to load.")
        return

    for voter in voters:
        try:
            # Path from DB should be like 'images/navana.jpg'
            image_path_relative = voter["face_photo"]
            if not image_path_relative:
                print(f"⚠️ Skipping NID {voter['NID']} due to missing image path.")
                continue

            name = voter["Name"]
            nid = voter["NID"]

            # THIS IS THE CRITICAL FIX: Construct the full path from the project root
            full_image_path = os.path.join(PROJECT_ROOT, image_path_relative.replace("\\", "/"))

            if not os.path.exists(full_image_path):
                print(f"❌ Error: Image file not found at '{full_image_path}' for NID {nid}")
                continue

            # Load and encode image
            image = face_recognition.load_image_file(full_image_path)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) > 0:
                known_face_encodings.append(encodings[0])
                known_face_ids.append(nid)
                known_face_names.append(name)
                print(f"✅ Loaded face encoding for: {name} (NID: {nid})")
            else:
                print(f"⚠️ No face could be detected in image: {full_image_path}")

        except Exception as e:
            print(f"❌ An unexpected error occurred loading image for NID {voter.get('NID', 'N/A')}: {e}")

    print(f"✅ Finished loading. Total voter encodings in memory: {len(known_face_encodings)}")


def compare_and_verify(live_image):
    """
    Compares the live face image against all stored encodings.
    Returns the NID of the matched voter or None.
    """
    global known_face_encodings, known_face_ids, known_face_names

    if not known_face_encodings:
        print("⚠️ Cannot verify face: No known face encodings are loaded.")
        return None

    live_face_locations = face_recognition.face_locations(live_image)
    live_face_encodings = face_recognition.face_encodings(live_image, live_face_locations)

    if not live_face_encodings:
        print("⚠️ No face detected in the live webcam image.")
        return None

    live_encoding = live_face_encodings[0]

    # Lower tolerance = stricter matching. 0.6 is default. 0.55 is a bit more forgiving for lighting.
    matches = face_recognition.compare_faces(known_face_encodings, live_encoding, tolerance=0.55)

    if True in matches:
        first_match_index = matches.index(True)
        matched_nid = known_face_ids[first_match_index]
        matched_name = known_face_names[first_match_index]
        print(f"✅ Face Matched! Live image matches {matched_name} (NID: {matched_nid})")
        return matched_nid

    print("❌ No match found for the face in the live image.")
    return None


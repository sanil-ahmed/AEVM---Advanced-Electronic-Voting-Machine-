import sqlite3
import os
from datetime import datetime

# --- Path Configuration ---
# Assumes the structure: project_root/backend/db.py and project_root/database/voters.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "..", "database", "voters.db")


def create_connection():
    """Establishes and returns a connection to the SQLite database file."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database at {DATABASE_FILE}: {e}")
        return None

# --- NEW FUNCTION FOR ENROLLMENT ---
def update_fingerprint_template(nid, template_b64):
    """Stores the Base64 encoded fingerprint template for a given NID."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # First, check if the voter exists
            cursor.execute("SELECT NID FROM voters WHERE NID = ?", (nid,))
            voter = cursor.fetchone()
            if voter:
                cursor.execute("UPDATE voters SET fingerprint_template = ? WHERE NID = ?", (template_b64, nid))
                conn.commit()
                return True  # Indicates success
            else:
                return False # Indicates NID not found
        except sqlite3.Error as e:
            print(f"Error updating fingerprint template: {e}")
            return False
        finally:
            conn.close()
    return False


# --- ALL OTHER FUNCTIONS FROM YOUR FILE (UNCHANGED) ---
def get_voter_by_nid(nid):
    """Retrieves a single voter record using the NID."""
    conn = create_connection()
    voter = None
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM voters WHERE NID=?", (nid,))
            voter = cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error retrieving voter: {e}")
        finally:
            if conn:
                conn.close()
    return voter


def get_all_voters():
    """Fetches all records from the voters table. REQUIRED BY face_utils.py"""
    conn = create_connection()
    voters_list = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT NID, Name, face_photo, fingerprint_template, is_voted, fingerprint_attempts FROM voters")
            voters_list = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving voters: {e}")
        finally:
            if conn:
                conn.close()
    return voters_list


def get_all_candidates():
    """Retrieves all candidates for the voting screen display."""
    conn = create_connection()
    candidates_list = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, photo_path, symbol_path FROM candidates")
            candidates_list = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving candidates: {e}")
        finally:
            if conn:
                conn.close()
    return candidates_list


def update_voter_attempts(nid, attempts):
    """Updates the fingerprint attempt count for a voter."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE voters SET fingerprint_attempts=? WHERE NID=?",
                (attempts, nid)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating attempts: {e}")
        finally:
            conn.close()
    return False


def log_vote(candidate_id, voter_nid):
    """Inserts a new vote, increments candidate total, and marks the voter as voted."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT is_voted FROM voters WHERE NID=?", (voter_nid,))
            voter_status = cursor.fetchone()
            if voter_status and voter_status['is_voted'] == 1:
                return False
            cursor.execute(
                "INSERT INTO votes (candidate_id, voter_nid, timestamp) VALUES (?, ?, ?)",
                (candidate_id, voter_nid, current_time)
            )
            cursor.execute(
                "UPDATE voters SET is_voted=1, fingerprint_attempts=0 WHERE NID=?",
                (voter_nid,)
            )
            cursor.execute(
                "UPDATE candidates SET vote_count = vote_count + 1 WHERE id=?",
                (candidate_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error logging vote: {e}")
        finally:
            if conn:
                conn.close()
    return False


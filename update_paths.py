import sqlite3
import os

# --- ⚙️ CONFIGURATION ---

# This script assumes it is being run from your main project folder
# (the one that contains the 'database' folder).
DB_FILE = os.path.join("database", "voters.db")

# This is the exact path from your screenshots that will be removed.
# This path is already set correctly for you based on your images.
ABSOLUTE_PATH_TO_REMOVE = "E:\\VotingApp_Project\\"

# List of all database locations (table, column) that store an image path.
# This is based on your db.py file and should be correct.
PATHS_TO_UPDATE = [
    ("voters", "face_photo"),      # Voter's face picture
    ("candidates", "photo_path"),  # Candidate's picture
    ("candidates", "symbol_path"), # Candidate's symbol image
]

# --- END OF CONFIGURATION ---


def update_database_paths():
    """
    Connects to the database and replaces the absolute path prefix
    with an empty string, making all image paths relative.
    """
    if not os.path.exists(DB_FILE):
        print(f"❌ FATAL ERROR: Database file not found at '{DB_FILE}'.")
        print("Please make sure you are running this script from your project's main folder.")
        return

    conn = None
    total_rows_affected = 0
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        print(f"🔗 Connected to database: {DB_FILE}")
        print(f"🗑️  Will remove this exact path prefix: '{ABSOLUTE_PATH_TO_REMOVE}'\n")

        for table, column in PATHS_TO_UPDATE:
            print(f"Processing -> Table: '{table}', Column: '{column}'")

            # SQL command to find and replace the absolute path prefix with nothing.
            # It only updates rows that actually start with the incorrect absolute path.
            sql_query = f"""
                UPDATE {table}
                SET {column} = REPLACE({column}, ?, '')
                WHERE {column} LIKE ?
            """

            # The LIKE pattern ensures we only touch the correct file paths
            like_pattern = ABSOLUTE_PATH_TO_REMOVE + '%'
            cursor.execute(sql_query, (ABSOLUTE_PATH_TO_REMOVE, like_pattern))

            rows_updated = cursor.rowcount
            total_rows_affected += rows_updated
            print(f"   -> ✔️  Found and updated {rows_updated} rows.\n")

        # Save all the changes to the database file
        conn.commit()
        print("--------------------------------------------------")
        print(f"✅✅✅ SUCCESS! All changes have been saved. ✅✅✅")
        print(f"Total rows modified across all tables: {total_rows_affected}")
        print("Your database now uses portable, relative paths!")
        print("You can now delete this script.")
        print("--------------------------------------------------")

    except sqlite3.Error as e:
        print(f"\n❌ DATABASE ERROR: {e}")
        if conn:
            conn.rollback() # Undo all changes if an error occurred
            print("   -> ❗️ All changes have been safely rolled back.")

    finally:
        if conn:
            conn.close()
            print("🔌 Database connection closed.")


# This line runs the main function when you execute the script from the terminal.
if __name__ == '__main__':
    update_database_paths()


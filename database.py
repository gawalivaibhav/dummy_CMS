import sqlite3
import logging
import datetime # Import datetime for timestamps

DATABASE = 'cms.db' # SQLite database file name

def get_db():
    """Connects to the specific database."""
    db = sqlite3.connect(DATABASE)
    # Set row_factory to get dictionary-like access to columns
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initializes the database by creating the sessions table if it doesn't exist."""
    db = get_db()
    with db: # Use 'with' for automatic commits/rollbacks
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idTag TEXT NOT NULL,
                startTime TEXT NOT NULL,
                endTime TEXT,
                status TEXT NOT NULL,
                meterValue REAL
            )
        ''')
        logging.info("Database initialized and sessions table ensured.")
    db.close() # Close connection after initialization

def create_session(id_tag, start_time, meter_start):
    """Creates a new charging session record in the database."""
    db = get_db()
    with db:
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO sessions (idTag, startTime, status, meterValue)
            VALUES (?, ?, ?, ?)
        ''', (id_tag, start_time, 'Charging', meter_start))
        session_id = cursor.lastrowid # Get the ID of the newly created row
    db.close()
    logging.info(f"Created session with ID: {session_id}")
    return session_id

def update_session(session_id, end_time, meter_stop, status='Finished'):
    """Updates an existing charging session record in the database."""
    db = get_db()
    with db:
        cursor = db.cursor()
        cursor.execute('''
            UPDATE sessions
            SET endTime = ?, status = ?, meterValue = ?
            WHERE id = ?
        ''', (end_time, status, meter_stop, session_id))
    db.close()
    logging.info(f"Updated session with ID: {session_id}")

def get_all_sessions():
    """Retrieves all charging session records from the database."""
    db = get_db()
    sessions = db.execute('SELECT * FROM sessions').fetchall()
    db.close()
    # Convert Row objects to dictionaries for jsonify
    sessions_list = [dict(row) for row in sessions]
    logging.info(f"Retrieved {len(sessions_list)} sessions from database.")
    return sessions_list

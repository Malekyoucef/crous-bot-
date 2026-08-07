import sqlite3

DB_FILE = "bot_data.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                region TEXT,
                is_restricted INTEGER DEFAULT 0
            )
        """)
        
        try:
            conn.execute("ALTER TABLE subscribers ADD COLUMN is_restricted INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass 
            
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                title TEXT,
                is_active INTEGER DEFAULT 1,
                location TEXT
            )
        """)

        try:
            conn.execute("ALTER TABLE rooms ADD COLUMN title TEXT")
            conn.execute("ALTER TABLE rooms ADD COLUMN is_active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
            
        # Add new column to remember the location of the room
        try:
            conn.execute("ALTER TABLE rooms ADD COLUMN location TEXT")
        except sqlite3.OperationalError:
            pass

def add_subscriber(chat_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))

def update_subscriber_region(chat_id, region):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
        conn.execute("UPDATE subscribers SET region = ? WHERE chat_id = ?", (region, chat_id))

def toggle_restrict(chat_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT is_restricted FROM subscribers WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if row is None:
            return False
        new_status = 0 if row[0] else 1
        conn.execute("UPDATE subscribers SET is_restricted = ? WHERE chat_id = ?", (new_status, chat_id))
        return bool(new_status)

def remove_subscriber(chat_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))

def get_subscribers():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT chat_id, region, is_restricted FROM subscribers")
        return {
            row[0]: {
                'region': row[1], 
                'is_restricted': bool(row[2])
            } for row in cursor.fetchall()
        }

def get_active_rooms():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT room_id, title, location FROM rooms WHERE is_active = 1")
        return {
            row[0]: {
                "title": row[1] or "Unknown", 
                "location": row[2] or ""
            } for row in cursor.fetchall()
        }

def add_or_update_room(room_id, title, location="", is_active=1):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("REPLACE INTO rooms (room_id, title, is_active, location) VALUES (?, ?, ?, ?)", (room_id, title, is_active, location))

def mark_room_inactive(room_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE rooms SET is_active = 0 WHERE room_id = ?", (room_id,))

init_db()
import sqlite3
from util import Util

def main():
    util = Util()
    conn = sqlite3.connect(util.get_database_path())
    cursor = conn.cursor()

    # author_id, name, added_date
    # file_id, author_id, name, date, size, link, added_date, downloaded_date

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS author (
                author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                added_date TEXT);
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS record (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                name TEXT,
                date TEXT,
                size INTEGER,
                link TEXT,
                added_date TEXT,
                downloaded_date TEXT);
    """)

    cursor.execute("""
    CREATE INDEX idx_author_name ON record(name);
    """)

    cursor.execute("""
    CREATE INDEX idx_record_author_id ON record(author_id);
    """)

    cursor.execute("""
    CREATE INDEX idx_record_link ON record(link);
    """)

    conn.commit()

if __name__ == "__main__":
    main()
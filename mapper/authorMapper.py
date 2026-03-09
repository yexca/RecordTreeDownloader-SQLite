from datetime import datetime
from db import Database

class AuthorMapper:
    def __init__(self):
        db = Database()
        self.conn = db.get_conn()
        self.cursor = self.conn.cursor()

    def get_author_id(self, name):
        self.cursor.execute(f"select author_id from author where name = ?", (name, ))
        row = self.cursor.fetchone()

        if row is None:
            return False
        return row[0]
    
    def search_author(self, name):
        self.cursor.execute(f"select * from author where name like ?", (f"%{name}%", ))
        rows = self.cursor.fetchall()
        return rows

    def get_author_name_by_id(self, authorId):    
        self.cursor.execute(f"select name from author where author_id = ?", (authorId, ))
        row = self.cursor.fetchone()
        return row[0]
    
    def add_author(self, name):
        date = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute(f"insert into author (name, added_date) values (?, ?)", (name, date, ))
        self.conn.commit()
        return self.cursor.lastrowid
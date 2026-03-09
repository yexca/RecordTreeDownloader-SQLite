from datetime import datetime
from db import Database

class RecordMapper:
    def __init__(self):
        db = Database()
        self.conn = db.get_conn()
        self.cursor = self.conn.cursor()
        self.UN_DOWNLOADED = 0

    def file_is_existed(self, link):
        self.cursor.execute("select * from record where link = ?", (link, ))
        row = self.cursor.fetchone()

        if row is None:
            return False
        return True
    
    def add_record(self, authorId, name, date, size, link):
        self.cursor.execute("""
            insert into 
            record (author_id, name, date, size, link, added_date, downloaded_date)
            values (?, ?, ?, ?, ?, ?, ?)
            """, (authorId, name, date, size, link, self.date_now(), self.UN_DOWNLOADED)
        )
        self.conn.commit()
        return True
    
    def get_download_links(self, authorId, count):
        self.cursor.execute("select * from record where author_id = ? and downloaded_date = ? limit ?", (authorId, self.UN_DOWNLOADED, count, ))
        return self.cursor.fetchall()
    
    def add_download_date(self, recordId):
        self.cursor.execute("update record set downloaded_date = ? where record_id = ?", (self.date_now(), recordId, ))
        self.conn.commit()
        return True

    def date_now(self):
        return datetime.now().strftime("%Y-%m-%d")
    
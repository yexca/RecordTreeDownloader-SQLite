import sqlite3
from util import Util

class Database:
    _instance = None

    def __init__(self):
        util = Util()
        self.conn = sqlite3.connect(util.get_database_path())
        self.conn.row_factory = sqlite3.Row
    
    def get_conn(self):
        if self._instance is None:
            self._instance = Database()
        return self._instance.conn
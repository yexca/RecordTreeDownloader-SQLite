import pandas as pd
import json
from util import Util
from mapper.authorMapper import AuthorMapper
from mapper.recordMapper import RecordMapper


def insert_record_xlsx():

    util = Util()
    RECORD_PATH = util.get_record_path()
    authorMapper = AuthorMapper()
    recordMapper = RecordMapper()

    # 读取数据 (以 Excel 为例)
    df = pd.read_excel(RECORD_PATH)

    for row in df.itertuples(index=True, name='Pandas'):
        # author
        authorName = getattr(row, '声优')
        authorId = authorMapper.get_author_id(authorName)
        if not authorId:
            # add record if not existed
            print(f"{authorName} is not existed")
            authorId = authorMapper.add_author(authorName)
            print(f"{authorName} added, author_id is {authorId}")
        print(f"{authorName} is existed, start recording")

        # mega str
        megaStr = getattr(row, 'MEGA')
        if pd.isna(megaStr):
            continue

        #record
        record = json.loads(megaStr)
        fileName = record["FileNames"]
        # fileDate = fileName.split("]")[1][1:]
        fileDate = getattr(row, '配信日期')
        if hasattr(fileDate, 'strftime'):
            fileDate = fileDate.strftime('%Y-%m-%d')
        properties = record["property"]
        # get link
        for p in properties:
            link = p["Link"]
            size = p["Size"]
            # file is existed
            if recordMapper.file_is_existed(link):
                print(f"file is existed, skip: {fileName}")
                continue
            print(f"file is not existed, add to database: {fileName}")
            recordMapper.add_record(authorId, fileName, fileDate, size, link)

if __name__ == "__main__":
    insert_record_xlsx()
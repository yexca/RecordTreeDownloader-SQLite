import json
from util import Util
from mapper.authorMapper import AuthorMapper
from mapper.recordMapper import RecordMapper

def insert_record():

    util = Util()
    RECORD_PATH = util.get_record_path()

    authorMapper = AuthorMapper()
    recordMapper = RecordMapper()

    with open(RECORD_PATH, "r", encoding="utf-8") as file:
        recordDatas = json.load(file)
        for authorData in recordDatas:
            authorName = authorData["author"]
            authorId = authorMapper.get_author_id(authorName)
            if authorId is False:
                # add record if not existed
                print(f"{authorName} is not existed")
                authorId = authorMapper.add_author(authorName)
                print(f"{authorName} added, author_id is {authorId}")
            print(f"{authorName} is existed, start recording")

            # get record
            for record in authorData["records"]:
                fileName = record["FileNames"]
                fileDate = fileName.split("]")[1][1:]
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
    insert_record()
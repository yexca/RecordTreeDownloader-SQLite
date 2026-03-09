from authorMapper import AuthorMapper
from recordMapper import RecordMapper
from mega import Mega
from util import Util

class Download:
    def __init__(self):
        self.authorMapper = AuthorMapper()
        self.recordMapper = RecordMapper()
        self.mega = Mega()
        self.util = Util()

    def start(self, authorId, authorName, count):
        if authorId <= 0 or authorId is None:
            print("没有 author id，将获取")
            authorId = self.authorMapper.get_author_id(authorName)
        if authorName == "" or authorName is None:
            print("没有 author name，将获取")
            authorName = self.authorMapper.get_author_name_by_id(authorId)
        if count == 0 or count is None:
            count = 3

        # get download link
        rows = self.recordMapper.get_download_links(authorId, count)

        for row in rows:
            # detect disk space
            size = row["size"]
            self.detect_disk_space(size)

            # download file
            link = row["link"]
            saveDir = self.util.get_save_dir(authorName)
            print(f"The file was saved to: {saveDir}")
            self.mega.download(link, saveDir)

            # add to database
            print("下载完成，准备写入数据库")
            self.recordMapper.add_download_date(row["record_id"])
            print("写入数据库完成")


    def detect_disk_space(self, size):
        freeSize = self.util.free_bytes_on_partition()
        if freeSize < 1 * 1024**3:
            print("剩余空间不足 1GB 请清理文件后重试")
            raise RuntimeError()
        elif freeSize < size:
            print(f"剩余空间不足文件大小 {self.util.fmt_bytes(size)}")
            raise RuntimeError()
        print("空间充足，准备下载")
        return True

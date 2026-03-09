import math, shutil
from pathlib import Path
import config

class Util:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.downloadDir = Path(config.DOWNLOAD_DIR)

    def get_database_path(self):
        return self.BASE_DIR / "database" / config.DATABASE_NAME
    
    def get_record_path(self):
        return self.BASE_DIR / "record" / config.DATA_NAME
    
    def get_save_dir(self, name):
        saveDir : Path = self.downloadDir / name
        saveDir.mkdir(parents=True, exist_ok=True)
        return saveDir



    # 查询剩余空间
    def free_bytes_on_partition(self) -> int:
        usage = shutil.disk_usage(self.downloadDir)
        return usage.free  # bytes


    def fmt_bytes(self, n: int) -> str:
        if n is None:
            return "Unknown"
        units = ["B","KB","MB","GB","TB","PB"]
        if n == 0:
            return "0 B"
        i = int(math.floor(math.log(n, 1024)))
        return f"{n / (1024 ** i):.2f} {units[i]}"
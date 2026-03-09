from mega import Mega
from download import Download
from authorMapper import AuthorMapper
from recordInsert import insert_record
from recordinsertbyxlsx import insert_record_xlsx
import config

def main():
    if config.RUN_MODE == 0:
        # search mode
        authorMapper = AuthorMapper()
        rows = authorMapper.search_author(config.SEARCH_NAME)
        # total = len(rows)
        print(f"Found {len(rows)} results:")
        for row in rows:
            print(dict(row))
        # raise SystemExit()
    elif config.RUN_MODE == 1:
        # download mode
        mega = Mega()
        mega.login_if_needed(config.MEGA_ACCOUNT, config.MEGA_PASSWORD)

        download = Download()
        download.start(config.DOWNLOAD_AUTHOR_ID, config.DOWNLOAD_AUTHOR_NAME, config.DOWNLOAD_COUNT)
    elif config.RUN_MODE == 2:
        # insert mode
        if config.DATA_MODE == 1:
            insert_record()
        elif config.DATA_MODE == 2:
            insert_record_xlsx()
        else:
            print("Please type right value for DATA_MODE")
    else:
        print("Please type right value for RUN_MODE")

if __name__ == "__main__":
    main()
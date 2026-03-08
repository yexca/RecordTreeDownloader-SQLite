from mega import Mega
from download import Download
from authorMapper import AuthorMapper
import config

def main():

    # search mode
    if config.SEARCH_NAME != "":
        authorMapper = AuthorMapper()
        rows = authorMapper.search_author(config.SEARCH_NAME)
        # total = len(rows)
        print(f"共找到 {len(rows)} 条结果:")
        for row in rows:
            print(dict(row))
        raise SystemExit()

    # download mode
    mega = Mega()
    mega.login_if_needed(config.MEGA_ACCOUNT, config.MEGA_PASSWORD)

    download = Download()
    download.start(config.DOWNLOAD_AUTHOR_ID, config.DOWNLOAD_AUTHOR_NAME, config.DOWNLOAD_COUNT)

if __name__ == "__main__":
    main()
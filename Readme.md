从某大佬给的 `Record Tree.json` 文件读取数据后存入 SQLite 数据库，然后实现下载功能

## 前置准备

使用需要先将该文件放在 `record` 文件夹下，然后执行 `python initSqlite.py` 初始化数据库，并将文件放入 `database` 文件夹下，执行 `python recordInsert.py` 以将数据插入数据库

## 下载配置

下载路径的配置在 `util.py` 文件，默认是 `D:/Downloads`，下载后的文件将按照作者名创建文件夹分类

## 使用说明

在 `main.py` 文件中，如果配置 `SEARCH_NAME` 将只是进行搜索，如果需要下载请同时配置以下四项并且安装 [MEGA CMD](https://mega.io/cmd)

- MEGA_ACCOUNT: MEGA 的账号
- MEGA_PASSWORD: MEGA 的密码
- DOWNLOAD_ID 或者 DOWNLOAD_NAME: 要下载的作者 ID 或名称
- DOWNLOAD_COUNT: 要下载的文件数量

然后执行命令 `python main.py` 即可

## 其他文件

另外 `Record.py` 是我刚开始写的文件，用于搜索和导出一个作者的所有数据，删除不影响程序使用

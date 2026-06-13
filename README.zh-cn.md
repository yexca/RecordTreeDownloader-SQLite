# RecordTreeDownloader SQLite

RecordTreeDownloader SQLite 是一个本地优先的 Python 命令行工具，用于把 Record Tree 元数据导入 SQLite，进行搜索，并通过 MEGAcmd 下载选中的 MEGA 链接。

这个工具不会抓取远程来源，不会保存 MEGA 凭据，也不提供图形界面。MEGA 登录状态由你本机的 MEGAcmd 管理。

## 安装

Windows 下推荐直接运行根目录的安装脚本：

```bat
run-install.bat
```

脚本会优先使用本机已有的 Python 3.11 或更高版本；如果本机没有可用 Python，会自动把 Python 3.12.10 安装到 `env/python`。项目依赖会安装到根目录 `.venv`，方便 VS Code 打开项目时自动识别解释器；运行时配置和数据仍保存在 `env/`。

安装完成后可以直接使用本地命令：

```powershell
.\.venv\Scripts\recordtree.exe doctor
```

如果本机已经有 Python 3，也可以使用轻量开发环境脚本：

```powershell
.\setup_env.ps1
```

下载功能仍需要 MEGAcmd。

## 初始化

创建本地配置、SQLite 数据库、下载目录和日志目录：

```bash
recordtree init
```

默认生成路径：

- 配置：`env/config.toml`
- 数据库：`env/recordtree.sqlite3`
- 下载目录：`downloads/`
- 日志目录：`logs/`
- 导入错误 CSV：`logs/import_<import_id>_errors.csv`

如需自定义路径、MEGAcmd 可执行文件名或下载安全余量，可以编辑 `env/config.toml`。

## 导入数据

Excel 主表、旧 SQLite 数据库和旧 JSON 导出都使用同一个导入命令：

```bash
recordtree import "files/Record Tree 260605.xlsx"
recordtree import files/record.db
recordtree import "files/Record Tree.Json"
```

推荐导入顺序是先导入 Excel 主表，再导入旧 SQLite 数据库，最后导入旧 JSON 导出。Excel 会作为最高质量的元数据来源；旧 SQLite 导入会通过已存在的活跃 URL 追加旧下载历史；JSON 仅作为较低优先级的兼容来源。

导入设计为可重复执行。工具会通过生成的 `source_key` 对记录组做 upsert；当同一记录的活跃链接集合变化时，会保留旧链接作为历史 inactive 链接。

导入大型旧数据库或进行大规模重新导入前，请备份 `env/recordtree.sqlite3`。如果存在 SQLite WAL 文件，也要同时备份 `env/recordtree.sqlite3-wal` 和 `env/recordtree.sqlite3-shm`，或使用 SQLite backup API。

## 搜索和查看

```bash
recordtree search-actor "<name>"
recordtree search-source niconico
recordtree search-title ASMR
recordtree search-date --from 2026-01-01 --to 2026-01-31
recordtree list-undownloaded --limit 20
recordtree info 123
recordtree stats
```

搜索命令不区分大小写，默认最多返回 50 行。

## 下载

先在本工具之外使用 MEGAcmd 登录：

```bash
mega-login
```

然后检查本地环境：

```bash
recordtree doctor
```

下载示例：

```bash
recordtree download 123 --types mp4,m4a
recordtree download 123 --include-par2 --yes
recordtree download 123 --output "D:/RecordTree/123"
```

默认会排除 `.par2` 文件。需要包含时使用 `--include-par2`。下载前工具会检查 MEGAcmd、登录状态、选中文件大小和磁盘可用空间，然后才调用 `mega-get`。

## 故障排查

常用命令：

```bash
recordtree doctor
recordtree stats
recordtree info <id>
recordtree list-undownloaded --limit 20
```

常见问题：

- 缺少配置或数据库：运行 `recordtree init`。
- 不支持的导入扩展名：使用 `.xlsx`、`.xlsm`、`.json`、`.db`、`.sqlite` 或 `.sqlite3`。
- 导入行错误：查看 `logs/import_<import_id>_errors.csv`。
- 找不到 MEGAcmd：安装 MEGAcmd，并确保 `mega-get` 和 `mega-whoami` 在 `PATH` 中，或在 `env/config.toml` 中配置可执行文件路径。
- 未登录 MEGA：手动运行 `mega-login`，再运行 `recordtree doctor`。
- 磁盘空间不足：更换 `--output`，释放空间，或调整 `env/config.toml` 中的安全余量。

## 测试

运行自动化测试：

```bash
pytest
```

MEGAcmd 相关测试使用 mock，不需要真实 MEGA 账号或网络访问。

## 维护文档

- [架构](documents/architecture.md)
- [数据契约](documents/data_contract.md)
- [测试指南](documents/testing_guide.md)

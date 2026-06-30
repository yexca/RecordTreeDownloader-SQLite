# RecordTreeDownloader SQLite

RecordTreeDownloader SQLite 是一个本地优先的 Record Tree 元数据管理和下载工具。它可以把 Excel、旧 SQLite、旧 JSON 数据导入 SQLite，支持搜索记录，并通过 MEGAcmd 下载选中的 MEGA 链接。

本工具不抓取远程来源，也不保存 MEGA 凭据。MEGA 登录状态由 MEGAcmd 自行管理。

## 功能

- 导入 Excel、旧 SQLite、旧 JSON。
- 按演员、标题、来源、日期范围和下载状态搜索。
- 查看记录组、活动链接和下载状态。
- 通过 MEGAcmd 下载链接。
- 支持 CLI 和 Docker WebUI。

## 快速开始

### Docker WebUI

```bash
docker compose build
docker compose up -d
docker compose exec recordtree-web recordtree init
docker compose exec recordtree-web mega-login
docker compose exec recordtree-web recordtree doctor
```

打开：

```text
http://127.0.0.1:7647
```

### CLI

Windows 下可以运行：

```bat
run-install.bat
```

然后初始化并检查环境：

```powershell
.\.venv\Scripts\recordtree.exe init
.\.venv\Scripts\recordtree.exe doctor
```

## 文档

- [文档索引](docs/README.md)
- [CLI 使用指南](docs/user-guide/cli.md)
- [WebUI 使用指南](docs/user-guide/webui.md)
- [Docker 部署](docs/user-guide/docker.md)
- [故障排查](docs/user-guide/troubleshooting.md)
- [架构](docs/maintainer-guide/architecture.md)
- [数据契约](docs/maintainer-guide/data-contract.md)
- [测试指南](docs/maintainer-guide/testing.md)

## 安全说明

- 不要提交真实导出、下载文件、MEGA 凭据或运行时数据库。
- 敏感的手动测试资料请放在 `real_test/`，该目录已被 Git 忽略。
- Docker 中的 MEGAcmd 登录状态保存在 `megacmd-home` 命名卷中。

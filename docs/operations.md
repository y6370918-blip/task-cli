# task-cli Operations Runbook

本文记录 task-cli 的启动、健康检查、数据库迁移、备份、恢复和发布验收流程。

当前 Docker Compose 配置适用于单实例演示和部署验收，不代表已经完成公网生产部署。

## Start Services

在仓库根目录执行：

```powershell
docker compose up -d --build --wait
docker compose ps
```

PostgreSQL 和 API 都应显示为 `healthy`。

API 容器启动顺序：

```text
等待 PostgreSQL healthy
→ alembic upgrade head
→ 启动 Uvicorn
→ /health/ready 检查数据库
```

## Health Checks

存活检查：

```powershell
Invoke-RestMethod `
    -Uri "http://localhost:8000/health/live"
```

预期返回 `alive`。

就绪检查：

```powershell
Invoke-RestMethod `
    -Uri "http://localhost:8000/health/ready"
```

预期返回 `ready`。

`live` 只证明 FastAPI 进程可以响应。

`ready` 还会执行数据库 `SELECT 1`。数据库不可用时返回 `503 Service Unavailable`。

## Logs

查看 API 日志：

```powershell
docker compose logs api --tail 100
```

持续跟踪：

```powershell
docker compose logs api --follow
```

日志中不应记录：

- JWT Secret；
- DeepSeek API Key；
- PostgreSQL 密码；
- Authorization Header；
- 完整数据库连接地址。

## Database Migration

查看代码迁移 head：

```powershell
docker compose exec api python -m alembic heads
```

确认数据库位于 head：

```powershell
docker compose exec api `
    python -m alembic current --check-heads
```

检查 ORM Model 与迁移结果是否一致：

```powershell
docker compose exec api python -m alembic check
```

不要在没有备份的情况下随意执行 Alembic downgrade。

## Database Backup

`pg_dump` 是只读操作，不会修改业务数据。

在仓库外创建备份目录：

```powershell
$backupDirectory = Join-Path `
    (Split-Path (Get-Location) -Parent) `
    "task-cli-backups"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $backupDirectory
```

在 PostgreSQL 容器中生成自定义格式备份：

```powershell
docker compose exec -T db sh -c `
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file=/tmp/task-cli.dump'
```

复制到仓库外：

```powershell
$backupName = "task-cli-$((Get-Date).ToString('yyyyMMdd-HHmmss')).dump"
$backupPath = Join-Path $backupDirectory $backupName

docker compose cp `
    db:/tmp/task-cli.dump `
    $backupPath
```

确认文件存在且不为空：

```powershell
Get-Item -LiteralPath $backupPath |
    Select-Object Name, Length, LastWriteTime
```

确认备份能被 `pg_restore` 读取：

```powershell
docker compose exec -T db `
    pg_restore --list /tmp/task-cli.dump
```

复制成功后，可以清理容器内的临时文件：

```powershell
docker compose exec -T db `
    rm -f /tmp/task-cli.dump
```

宿主机备份可能包含用户数据和密码哈希，不能提交到 Git，也不能公开分享。

## Restore Rehearsal

不要直接覆盖当前的 `task_db`。

恢复演练必须使用全新的专用数据库，例如：

```text
task_restore_test
```

把备份复制回容器：

```powershell
docker compose cp `
    $backupPath `
    db:/tmp/task-cli-restore.dump
```

创建空的恢复测试数据库：

```powershell
docker compose exec -T db sh -c `
    'createdb -U "$POSTGRES_USER" task_restore_test'
```

恢复备份：

```powershell
docker compose exec -T db sh -c `
    'pg_restore -U "$POSTGRES_USER" -d task_restore_test /tmp/task-cli-restore.dump'
```

验证恢复数据库中的迁移版本：

```powershell
docker compose exec -T db sh -c `
    'psql -U "$POSTGRES_USER" -d task_restore_test -c "SELECT version_num FROM alembic_version;"'
```

只有明确确认恢复演练完成后，才能删除专用恢复测试数据库：

```powershell
docker compose exec -T db sh -c `
    'dropdb -U "$POSTGRES_USER" task_restore_test'
```

不要对真实业务数据库名称运行 `dropdb`。

## Stop Services

停止并删除容器和网络，同时保留数据库 Volume：

```powershell
docker compose down
```

普通停止流程只允许使用上面的命令。

不要为该命令添加删除 Volume 的选项。删除 Volume 会让当前 PostgreSQL 数据目录消失，只能依靠已经验证的数据库备份恢复。

## Release Checklist

发布前逐项确认：

- `git status --short` 没有意外文件；
- `git diff --check` 通过；
- Ruff lint 通过；
- Ruff format check 通过；
- mypy 通过；
- 完整 pytest 通过；
- PostgreSQL 集成测试通过；
- Alembic 数据库位于 head；
- `alembic check` 没有新操作；
- Docker 镜像构建成功；
- API 容器使用非 root 用户；
- `live` 和 `ready` 健康检查通过；
- 已生成并验证数据库备份；
- `.env` 没有被 Git 跟踪；
- 日志没有暴露密钥；
- CI 通过后再创建版本标签。

## Deployment Boundary

当前仍有以下生产边界：

- 没有公网托管平台、域名和 TLS；
- 没有 API 级限流；
- 没有集中式日志和监控平台；
- Compose 启动时自动迁移，只适合当前单实例；
- 多副本部署时应把迁移改成独立发布步骤；
- Python 依赖尚未使用完整 lock file 固定传递依赖；
- Git remote 尚未配置；
- GitHub Actions 和 GitHub Release 尚未实际验证。

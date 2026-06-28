# deepagents-docker-sandbox

Docker sandbox backend for [deepagents](https://github.com/jbpayton/deepagents) - 让 AI Agent 在隔离的 Docker 容器中安全地执行代码和操作文件。

## 安装

```bash
pip install deepagents-docker-sandbox
```

## 快速开始

```python
from deepagents_docker_sandbox import DockerSandbox

# 使用 context manager，退出时自动清理容器
with DockerSandbox(image="python:3.13-slim") as sandbox:
    # 执行命令
    result = sandbox.execute("echo 'Hello from Docker!'")
    print(result.output)       # Hello from Docker!
    print(result.exit_code)    # 0

    # 写入文件
    sandbox.write("/workspace/test.txt", "Hello, World!")

    # 读取文件
    read_result = sandbox.read("/workspace/test.txt")
    print(read_result.file_data["content"])  # Hello, World!

    # 列出目录
    ls_result = sandbox.ls("/workspace")
    for entry in ls_result.entries:
        print(entry["path"])

    # 编辑文件
    sandbox.edit("/workspace/test.txt", "Hello", "你好")
```

## 主要功能

| 方法 | 说明 |
|------|------|
| `execute(command, timeout=None)` | 在容器内执行 shell 命令 |
| `write(path, content)` | 写入文件 |
| `read(path)` | 读取文件 |
| `edit(path, old_string, new_string)` | 编辑文件 |
| `ls(path)` | 列出目录内容 |
| `grep(pattern, path)` | 搜索文件内容 |
| `glob(pattern, path)` | 按模式匹配文件 |
| `upload_files(files)` | 批量上传文件 |
| `download_files(paths)` | 批量下载文件 |
| `close()` | 关闭沙箱，停止并删除容器 |

## 配置选项

```python
DockerSandbox(
    image="python:3.13-slim",           # Docker 镜像
    container_name="my-sandbox",        # 容器名称（默认自动生成）
    volumes={"/host": {"bind": "/container", "mode": "rw"}},  # 卷挂载
    working_dir="/workspace",           # 工作目录
    auto_remove=True,                   # 关闭时自动删除容器
    execute_timeout=120,                # 命令超时（秒）
    max_output_bytes=500*1024,          # 最大输出字节数
    docker_client_kwargs={},            # 传递给 docker.from_env() 的参数
)
```

## 前置条件

- Python >= 3.11
- Docker 已安装并运行
- 当前用户有 Docker 权限（或在 `docker` 用户组中）

## 许可证

MIT

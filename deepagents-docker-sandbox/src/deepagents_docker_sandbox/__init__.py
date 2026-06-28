"""deepagents-docker-sandbox: Docker sandbox backend for deepagents.

让 AI Agent 可以在隔离的 Docker 容器中安全地执行代码和操作文件。

快速开始:
    from deepagents_docker_sandbox import DockerSandbox

    with DockerSandbox(image="python:3.13-slim") as sandbox:
        result = sandbox.execute("echo 'Hello!'")
        print(result.output)
"""

from deepagents_docker_sandbox.sandbox import DockerSandbox

__all__ = ["DockerSandbox"]
__version__ = "0.1.0"

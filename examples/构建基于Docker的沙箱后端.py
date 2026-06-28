"""Docker Sandbox 实现 - 基于 Docker 容器的沙箱后端。

使用 Docker SDK for Python 实现 deepagents 的 BaseSandbox 抽象类，
让 AI Agent 可以在隔离的 Docker 容器中安全地执行代码和操作文件。

使用方法:
    with DockerSandbox(image="python:3.13-slim") as sandbox:
        # 执行命令
        result = sandbox.execute("echo 'Hello!'")

        # 文件操作
        sandbox.write("/workspace/test.txt", "content")
        read_result = sandbox.read("/workspace/test.txt")
"""

from __future__ import annotations

import io
import json
import logging
import tarfile
import threading
import uuid
from typing import Any

import docker
from docker.models.containers import Container

from deepagents.backends.sandbox import BaseSandbox
from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_IMAGE = "python:3.13-slim"
DEFAULT_WORKING_DIR = "/workspace"
DEFAULT_EXECUTE_TIMEOUT = 120  # 秒
DEFAULT_MAX_OUTPUT_BYTES = 500 * 1024  # 500KB


class DockerSandbox(BaseSandbox):
    """基于 Docker 容器的沙箱实现。

    通过 Docker SDK for Python 管理容器生命周期，所有文件操作和命令执行
    都在容器内完成，提供安全的隔离环境。

    Attributes:
        image: Docker 镜像名称
        container: Docker 容器对象
        working_dir: 容器内工作目录
    """

    def __init__(
            self,
            image: str = DEFAULT_IMAGE,
            container_name: str | None = None,
            volumes: dict[str, dict[str, str]] | None = None,
            working_dir: str = DEFAULT_WORKING_DIR,
            auto_remove: bool = True,
            execute_timeout: int = DEFAULT_EXECUTE_TIMEOUT,
            max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
            docker_client_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """初始化 Docker 沙箱。

        Args:
            image: Docker 镜像名称，默认 python:3.13-slim
            container_name: 容器名称，不指定则自动生成
            volumes: 卷挂载配置，格式如 {"/host/path": {"bind": "/container/path", "mode": "rw"}}
            working_dir: 容器内工作目录
            auto_remove: 关闭时是否自动删除容器
            execute_timeout: 命令执行默认超时时间（秒）
            max_output_bytes: 输出最大字节数
            docker_client_kwargs: 传递给 docker.from_env() 的额外参数
        """
        self._image = image
        self._container_name = container_name or f"sandbox-{uuid.uuid4().hex[:12]}"
        self._volumes = volumes or {}
        self._working_dir = working_dir
        self._auto_remove = auto_remove
        self._default_timeout = execute_timeout
        self._max_output_bytes = max_output_bytes

        # 初始化 Docker 客户端
        client_kwargs = docker_client_kwargs or {}
        self._client = docker.from_env(**client_kwargs)

        # 创建并启动容器
        self._container = self._create_container()

        # 确保工作目录存在
        self.execute(f"mkdir -p {working_dir}")

        logger.info(
            "DockerSandbox initialized: container=%s, image=%s",
            self._container.short_id,
            image,
        )

    def _create_container(self) -> Container:
        """创建并启动 Docker 容器。

        Returns:
            创建的容器对象
        """
        container = self._client.containers.run(
            image=self._image,
            name=self._container_name,
            command="tail -f /dev/null",  # 保持容器运行
            working_dir=self._working_dir,
            volumes=self._volumes,
            detach=True,
            stdin_open=True,
            tty=False,
        )
        return container

    @property
    def id(self) -> str:
        """容器的唯一标识符。"""
        return self._container.short_id

    @property
    def container(self) -> Container:
        """Docker 容器对象。"""
        return self._container

    def execute(
            self,
            command: str,
            *,
            timeout: int | None = None,
    ) -> ExecuteResponse:
        """在容器内执行 shell 命令。

        Args:
            command: 要执行的 shell 命令
            timeout: 超时时间（秒），None 则使用默认值

        Returns:
            ExecuteResponse 包含输出、退出码和截断标志
        """
        if not command or not isinstance(command, str):
            return ExecuteResponse(
                output="Error: Command must be a non-empty string.",
                exit_code=1,
                truncated=False,
            )

        effective_timeout = timeout if timeout is not None else self._default_timeout

        # 用于存储执行结果
        result_holder: dict[str, Any] = {}
        execution_done = threading.Event()

        def run_command() -> None:
            """在线程中执行命令。"""
            try:
                exit_code, output = self._container.exec_run(
                    cmd=["sh", "-c", command],
                    stdout=True,
                    stderr=True,
                    demux=False,  # 合并 stdout 和 stderr
                    workdir=self._working_dir,
                )
                result_holder["exit_code"] = exit_code
                result_holder["output"] = output.decode("utf-8", errors="replace") if output else ""
            except Exception as e:
                result_holder["exit_code"] = 1
                result_holder["output"] = f"Error executing command: {type(e).__name__}: {e}"
            finally:
                execution_done.set()

        # 在线程中执行，支持超时
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()

        if not execution_done.wait(timeout=effective_timeout):
            # 超时 - 尝试获取容器内进程列表并清理
            try:
                self._container.exec_run(cmd=["sh", "-c", "pkill -f sh -c || true"])
            except Exception:
                pass
            return ExecuteResponse(
                output=f"Error: Command timed out after {effective_timeout} seconds.",
                exit_code=124,  # 标准超时退出码
                truncated=False,
            )

        output = result_holder.get("output", "")
        exit_code = result_holder.get("exit_code", 1)

        # 检查输出截断
        truncated = False
        if len(output.encode("utf-8")) > self._max_output_bytes:
            output = output[:self._max_output_bytes]
            output += f"\n\n... Output truncated at {self._max_output_bytes} bytes."
            truncated = True

        return ExecuteResponse(
            output=output,
            exit_code=exit_code,
            truncated=truncated,
        )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """上传文件到容器。

        将文件打包成 tar 归档，通过 Docker API 传输到容器内。

        Args:
            files: 文件列表，每项为 (path, content) 元组

        Returns:
            FileUploadResponse 列表，每个文件一个响应
        """
        responses: list[FileUploadResponse] = []

        for file_path, content in files:
            try:
                # 确保路径是绝对路径
                if not file_path.startswith("/"):
                    file_path = f"{self._working_dir}/{file_path}"

                # 获取目录路径
                dir_path = file_path.rsplit("/", 1)[0] if "/" in file_path else "/"

                # 创建 tar 归档
                tar_stream = io.BytesIO()
                with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                    # 添加文件到 tar
                    file_data = content
                    info = tarfile.TarInfo(name=file_path.lstrip("/"))
                    info.size = len(file_data)
                    tar.addfile(info, io.BytesIO(file_data))

                tar_stream.seek(0)

                # 先创建目录（如果不存在）
                self.execute(f"mkdir -p {dir_path}")

                # 上传到容器根目录
                self._container.put_archive("/", tar_stream)

                responses.append(FileUploadResponse(path=file_path, error=None))
                logger.debug("Uploaded file: %s (%d bytes)", file_path, len(content))

            except Exception as e:
                error_msg = f"Failed to upload {file_path}: {type(e).__name__}: {e}"
                logger.error(error_msg)
                responses.append(FileUploadResponse(path=file_path, error=error_msg))

        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """从容器下载文件。

        通过 Docker API 获取文件的 tar 归档并解包。

        Args:
            paths: 文件路径列表

        Returns:
            FileDownloadResponse 列表，每个文件一个响应
        """
        responses: list[FileDownloadResponse] = []

        for file_path in paths:
            try:
                # 确保路径是绝对路径
                if not file_path.startswith("/"):
                    file_path = f"{self._working_dir}/{file_path}"

                # 获取文件的 tar 流
                tar_stream, stat = self._container.get_archive(file_path)

                # 从 tar 中提取文件内容
                tar_data = io.BytesIO()
                for chunk in tar_stream:
                    tar_data.write(chunk)
                tar_data.seek(0)

                with tarfile.open(fileobj=tar_data, mode="r") as tar:
                    # 获取第一个文件（应该只有一个）
                    members = tar.getmembers()
                    if not members:
                        responses.append(FileDownloadResponse(
                            path=file_path,
                            content=None,
                            error="file_not_found",
                        ))
                        continue

                    # 读取文件内容
                    member = members[0]
                    f = tar.extractfile(member)
                    if f is None:
                        responses.append(FileDownloadResponse(
                            path=file_path,
                            content=None,
                            error="file_not_found",
                        ))
                        continue

                    content = f.read()
                    responses.append(FileDownloadResponse(
                        path=file_path,
                        content=content,
                        error=None,
                    ))
                    logger.debug("Downloaded file: %s (%d bytes)", file_path, len(content))

            except docker.errors.NotFound:
                responses.append(FileDownloadResponse(
                    path=file_path,
                    content=None,
                    error="file_not_found",
                ))
            except Exception as e:
                error_msg = f"Failed to download {file_path}: {type(e).__name__}: {e}"
                logger.error(error_msg)
                responses.append(FileDownloadResponse(
                    path=file_path,
                    content=None,
                    error=error_msg,
                ))

        return responses

    def close(self) -> None:
        """关闭沙箱，停止并删除容器。"""
        try:
            if self._auto_remove:
                self._container.stop(timeout=5)
                self._container.remove(force=True)
                logger.info("Container %s removed", self._container.short_id)
            else:
                self._container.stop(timeout=5)
                logger.info("Container %s stopped", self._container.short_id)
        except Exception as e:
            logger.warning("Error closing container: %s", e)
        finally:
            self._client.close()

    def __enter__(self) -> DockerSandbox:
        """Context manager 入口。"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager 出口，自动关闭容器。"""
        self.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Docker Sandbox 测试")
    print("=" * 60)

    # 使用 context manager 确保容器被清理
    with DockerSandbox(image="python:3.13-slim") as sandbox:
        print(f"\n容器 ID: {sandbox.id}")

        # 测试 1: 基本命令执行
        print("\n--- 测试 1: 基本命令执行 ---")
        result = sandbox.execute("echo 'Hello from Docker!'")
        print(f"输出: {result.output.strip()}")
        print(f"退出码: {result.exit_code}")

        # 测试 2: Python 执行
        print("\n--- 测试 2: Python 执行 ---")
        result = sandbox.execute("python3 -c 'import sys; print(f\"Python {sys.version}\")'")
        print(f"输出: {result.output.strip()}")

        # 测试 3: 写入文件
        print("\n--- 测试 3: 写入文件 ---")
        write_result = sandbox.write("/workspace/test.txt", "Hello, World!\n这是测试内容。")
        print(f"写入结果: path={write_result.path}, error={write_result.error}")

        # 测试 4: 读取文件
        print("\n--- 测试 4: 读取文件 ---")
        read_result = sandbox.read("/workspace/test.txt")
        if read_result.file_data:
            print(f"文件内容:\n{read_result.file_data['content']}")
        else:
            print(f"读取错误: {read_result.error}")

        # 测试 5: 列出目录
        print("\n--- 测试 5: 列出目录 ---")
        ls_result = sandbox.ls("/workspace")
        if ls_result.entries:
            for entry in ls_result.entries:
                print(f"  {entry['path']} (dir={entry.get('is_dir', False)})")

        # 测试 6: 编辑文件
        print("\n--- 测试 6: 编辑文件 ---")
        edit_result = sandbox.edit("/workspace/test.txt", "Hello", "你好")
        print(f"编辑结果: path={edit_result.path}, occurrences={edit_result.occurrences}")

        # 验证编辑
        read_result = sandbox.read("/workspace/test.txt")
        if read_result.file_data:
            print(f"编辑后内容:\n{read_result.file_data['content']}")

        # 测试 7: 超时测试
        print("\n--- 测试 7: 超时测试 ---")
        result = sandbox.execute("sleep 10", timeout=2)
        print(f"输出: {result.output.strip()}")
        print(f"退出码: {result.exit_code}")

    print("\n" + "=" * 60)
    print("测试完成！容器已自动清理。")
    print("=" * 60)

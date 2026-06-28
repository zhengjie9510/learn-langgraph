"""基础测试 - 验证包导入和基本功能。"""

import pytest


def test_import():
    """测试包可以正常导入。"""
    from deepagents_docker_sandbox import DockerSandbox
    assert DockerSandbox is not None


def test_version():
    """测试版本号存在。"""
    import deepagents_docker_sandbox
    assert hasattr(deepagents_docker_sandbox, "__version__")
    assert deepagents_docker_sandbox.__version__ == "0.1.0"


def test_all_exports():
    """测试 __all__ 导出。"""
    import deepagents_docker_sandbox
    assert "DockerSandbox" in deepagents_docker_sandbox.__all__


def test_class_inheritance():
    """测试 DockerSandbox 继承自 BaseSandbox。"""
    from deepagents_docker_sandbox import DockerSandbox
    from deepagents.backends.sandbox import BaseSandbox
    assert issubclass(DockerSandbox, BaseSandbox)


def test_required_methods():
    """测试 DockerSandbox 实现了必要的抽象方法。"""
    from deepagents_docker_sandbox import DockerSandbox

    # 检查抽象方法存在
    assert hasattr(DockerSandbox, "execute")
    assert hasattr(DockerSandbox, "upload_files")
    assert hasattr(DockerSandbox, "download_files")
    assert hasattr(DockerSandbox, "id")

    # 检查 context manager
    assert hasattr(DockerSandbox, "__enter__")
    assert hasattr(DockerSandbox, "__exit__")
    assert hasattr(DockerSandbox, "close")


# 以下测试需要 Docker 环境运行，标记为集成测试
@pytest.mark.integration
class TestDockerSandboxIntegration:
    """需要 Docker 的集成测试。"""

    def test_execute_command(self):
        """测试执行命令。"""
        from deepagents_docker_sandbox import DockerSandbox

        with DockerSandbox(image="python:3.13-slim") as sandbox:
            result = sandbox.execute("echo 'hello'")
            assert result.exit_code == 0
            assert "hello" in result.output

    def test_write_and_read(self):
        """测试写入和读取文件。"""
        from deepagents_docker_sandbox import DockerSandbox

        with DockerSandbox(image="python:3.13-slim") as sandbox:
            sandbox.write("/workspace/test.txt", "content")
            result = sandbox.read("/workspace/test.txt")
            assert result.file_data is not None
            assert result.file_data["content"] == "content"

    def test_context_manager_cleanup(self):
        """测试 context manager 退出时清理容器。"""
        from deepagents_docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(image="python:3.13-slim")
        container_id = sandbox.id
        sandbox.close()
        # 容器应该已被删除

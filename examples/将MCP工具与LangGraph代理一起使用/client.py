import asyncio
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            # 这里必须换成你的 math_server.py 的绝对路径
            "args": [
                "math_server.py"],
            "transport": "stdio",
        },
        "weather": {
            "url": "http://127.0.0.1:8000/mcp/",
            "transport": "streamable_http",
        },
    }
)


async def main():
    model = ChatOpenAI(model='qwen-plus')
    tools = await client.get_tools()
    print(tools)


if __name__ == "__main__":
    asyncio.run(main())

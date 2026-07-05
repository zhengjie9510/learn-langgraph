"""Claude Code 请求拦截器 - 用于观察 Cloud Code 发送的 API 请求内容。

启动服务后，将 Claude Code 的 API 端点指向 http://127.0.0.1:8000，
请求内容会同时输出到控制台和写入 requests.jsonl 文件。
"""

import json
import time
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()


@app.post("/{full_path:path}")
async def catch_all(full_path: str, request: Request):
    print(f"\n{'='*60}")
    print(f"[请求] POST /{full_path}")

    # 打印关键的请求头
    for key, value in request.headers.items():
        if key.lower().startswith("anthropic") or key.lower() in ("user-agent", "content-type"):
            print(f"  [Header] {key}: {value}")

    # 每次请求写入单独的文件
    body = await request.json()
    filename = f"requests_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    record = {
        "url_path": f"/{full_path}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "headers": {k: v for k, v in request.headers.items()
                    if k.lower().startswith("anthropic") or k.lower() in ("user-agent", "content-type")},
        "body": body,
    }
    with open(filename, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  [日志] 已写入 {filename}")

    print(f"{'='*60}\n")

    # 返回模拟的 SSE 流式响应，让 Claude Code 正常运行
    async def fake_stream():
        yield (
            "event: message_start\n"
            "data: {\"type\":\"message_start\",\"message\":{\"id\":\"msg_mock\","
            "\"type\":\"message\",\"role\":\"assistant\",\"content\":[],"
            "\"model\":\"mock-model\"}}\n\n"
        )
        yield (
            "event: content_block_start\n"
            "data: {\"type\":\"content_block_start\",\"index\":0,"
            "\"content_block\":{\"type\":\"text\",\"text\":\"\"}}\n\n"
        )
        yield (
            "event: content_block_delta\n"
            "data: {\"type\":\"content_block_delta\",\"index\":0,"
            "\"delta\":{\"type\":\"text_delta\",\"text\":\"[Mock] 请求已收到！\"}}\n\n"
        )
        yield (
            "event: content_block_stop\n"
            "data: {\"type\":\"content_block_stop\",\"index\":0}\n\n"
        )
        yield "event: message_stop\ndata: {\"type\":\"message_stop\"}\n\n"

    return StreamingResponse(fake_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

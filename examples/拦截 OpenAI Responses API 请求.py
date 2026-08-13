"""拦截 OpenAI Responses API 请求 - 用于观察客户端发送的 API 请求内容。

启动服务后，将客户端的 API 端点指向 http://127.0.0.1:8000，
请求内容会同时输出到控制台和写入 requests_*.jsonl 文件。
"""

import json
import time
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()


@app.post("/{full_path:path}")
async def catch_all(full_path: str, request: Request):
    print(f"\n{'=' * 60}")
    print(f"[请求] POST /{full_path}")

    # 打印关键的请求头
    for key, value in request.headers.items():
        if key.lower().startswith("openai") or key.lower() in ("user-agent", "content-type"):
            print(f"  [Header] {key}: {value}")

    # 每次请求写入单独的文件
    body = await request.json()
    filename = f"requests_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    record = {
        "url_path": f"/{full_path}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "headers": {k: v for k, v in request.headers.items()
                    if k.lower().startswith("openai") or k.lower() in ("user-agent", "content-type")},
        "body": body,
    }
    with open(filename, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  [日志] 已写入 {filename}")

    print(f"{'=' * 60}\n")

    # 返回模拟的 SSE 流式响应（OpenAI Responses API 事件格式），让客户端正常运行
    model = body.get("model", "mock-model")
    created_at = int(time.time())
    mock_text = "[Mock] 请求已收到！"

    def sse(event_type: str, payload: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def fake_stream():
        # sequence_number 从 0 递增，与官方流式事件格式一致
        yield sse("response.created", {
            "type": "response.created", "sequence_number": 0,
            "response": {"id": "resp_mock", "created_at": created_at, "object": "response",
                         "status": "queued", "model": model, "output": []},
        })
        yield sse("response.in_progress", {
            "type": "response.in_progress", "sequence_number": 1,
            "response": {"id": "resp_mock", "created_at": created_at, "object": "response",
                         "status": "in_progress", "model": model, "output": []},
        })
        yield sse("response.output_item.added", {
            "type": "response.output_item.added", "sequence_number": 2, "output_index": 0,
            "item": {"id": "msg_mock", "type": "message", "status": "in_progress",
                     "role": "assistant", "content": []},
        })
        yield sse("response.content_part.added", {
            "type": "response.content_part.added", "sequence_number": 3,
            "item_id": "msg_mock", "output_index": 0, "content_index": 0,
            "part": {"type": "output_text", "text": "", "annotations": [], "logprobs": None},
        })
        yield sse("response.output_text.delta", {
            "type": "response.output_text.delta", "sequence_number": 4,
            "item_id": "msg_mock", "output_index": 0, "content_index": 0,
            "delta": mock_text, "logprobs": [],
        })
        yield sse("response.output_text.done", {
            "type": "response.output_text.done", "sequence_number": 5,
            "item_id": "msg_mock", "output_index": 0, "content_index": 0,
            "text": mock_text, "logprobs": [],
        })
        yield sse("response.content_part.done", {
            "type": "response.content_part.done", "sequence_number": 6,
            "item_id": "msg_mock", "output_index": 0, "content_index": 0,
            "part": {"type": "output_text", "text": mock_text, "annotations": [], "logprobs": None},
        })
        yield sse("response.output_item.done", {
            "type": "response.output_item.done", "sequence_number": 7, "output_index": 0,
            "item": {"id": "msg_mock", "type": "message", "status": "completed", "role": "assistant",
                     "content": [{"type": "output_text", "text": mock_text,
                                  "annotations": [], "logprobs": None}]},
        })
        yield sse("response.completed", {
            "type": "response.completed", "sequence_number": 8,
            "response": {"id": "resp_mock", "created_at": created_at, "object": "response",
                         "status": "completed", "model": model,
                         "output": [{"id": "msg_mock", "type": "message", "status": "completed",
                                     "role": "assistant",
                                     "content": [{"type": "output_text", "text": mock_text,
                                                  "annotations": [], "logprobs": None}]}],
                         "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}},
        })

    return StreamingResponse(fake_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

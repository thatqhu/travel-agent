from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supervisor import travel_graph
from langchain_core.messages import HumanMessage
import json
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/chat/stream")
async def chat_stream(message: str):
    async def event_generator():
        # 发送开始信号
            yield f"data: {json.dumps({'type': 'token', 'content': '开始制定旅行计划...'})}\n\n"

            async for event in travel_graph.astream_events(
                {"messages": [("user", message)]},
                version="v2",
                config={"recursion_limit": 100}
            ):
                kind = event["event"]

                # 捕获LLM思考过程
                if kind == "on_chain_stream" and event["name"] != "supervisor" and event["name"] != "LangGraph":
                    content = event["data"]["chunk"].update["messages"][-1].content
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

                # 节点开始事件
                elif kind == "on_chain_start":
                    name = event.get("name", "")
                    if "hotel" in name.lower():
                        yield f"data: {json.dumps({'type': 'tool', 'content': '🏨 正在搜索和评估酒店...'}, ensure_ascii=False)}\n\n"
                    elif "itinerary" in name.lower() or "attraction" in name.lower():
                        yield f"data: {json.dumps({'type': 'tool', 'content': '📍 正在规划景点和行程...'}, ensure_ascii=False)}\n\n"
                    elif "final" in name.lower():
                        yield f"data: {json.dumps({'type': 'tool', 'content': '✈️ 正在生成最终旅行计划...'}, ensure_ascii=False)}\n\n"

                # 节点完成事件 - 输出阶段性结果
                elif kind == "on_chain_end":
                    name = event.get("name", "")
                    data = event.get("data", {})

                    if "output" in data and isinstance(data["output"], dict):
                        messages = data["output"].get("messages", [])
                        if messages:
                            last_message = messages[-1]
                            content = getattr(last_message, "content", "")

                            if content and len(content) > 10:  # 过滤太短的消息
                                yield f"data: {json.dumps({'type': 'result', 'content': content}, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0.1)  # 给前端渲染时间

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'content': '旅行计划制定完成！'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

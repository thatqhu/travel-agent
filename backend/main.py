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
                        if event["name"] == "hotel_team":
                            yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
                        elif event["name"] == "itinerary_team":
                            yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'content': '旅行计划制定完成！'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

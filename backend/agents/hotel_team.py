import os
from typing import Literal
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from tools.hotel_tool import search_hotels, evaluate_hotels

api_key_val = os.environ.get("DASHSCOPE_API_KEY")
if not api_key_val:
    raise ValueError("DASHSCOPE_API_KEY is not set")
llm = ChatOpenAI(
    model="qwen-plus",
    api_key=SecretStr(api_key_val),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.5
)

# 酒店搜索代理
hotel_searcher = create_agent(
    llm,
    tools=[search_hotels]
)

# 酒店搜索代理
hotel_evaluator = create_agent(
    llm,
    tools=[evaluate_hotels]
)

class HotelState(MessagesState):
    next: str

def searcher_node(state: HotelState) -> Command[Literal["supervisor"]]:
    system_prompt = (
        "你是酒店搜索专家，专注查找酒店，忽略入住和退房的日期等信息，使用提供的工具搜索酒店信息，按照地理位置远近，返回最近的1家的经济型酒店。不需要安排行程。"
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    result = hotel_searcher.invoke({"messages": messages})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"[酒店搜索] {result['messages'][-1].content}",
                    name="hotel_searcher"
                )
            ]
        },
        goto="supervisor"
    )

def evaluator_node(state: HotelState) -> Command[Literal["supervisor"]]:
    system_prompt = (
        "你是酒店评估专家，负责分析酒店的位置、设施、评价和性价比，对于给定的第一个酒店给出一句话的总结."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    result = hotel_evaluator.invoke({"messages": messages})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"[酒店评估] {result['messages'][-1].content}",
                    name="hotel_evaluator"
                )
            ]
        },
        goto="supervisor"
    )

def hotel_supervisor(state: HotelState) -> Command:
    """酒店团队监督者"""
    from typing_extensions import TypedDict

    class Router(TypedDict):
        next: Literal["searcher", "evaluator", "FINISH"]

    system_prompt = (
        "你是酒店团队主管,"
        "规则："
        "1. 是否使用 searcher 搜索过酒店?"
        "2. 是否使用 evaluator 评估过酒店?"
        "如果都完成了,返回 FINISH 结束,注意,结束前返回json格式数据, 示例: {'next': 'searcher'}."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]

    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]

    if goto == "FINISH":
        goto = "__end__"

    return Command(goto=goto, update={"next": goto})

# 构建酒店团队图
hotel_builder = StateGraph(HotelState)
hotel_builder.add_node("supervisor", hotel_supervisor)
hotel_builder.add_node("searcher", searcher_node)
hotel_builder.add_node("evaluator", evaluator_node)
hotel_builder.add_edge(START, "supervisor")
hotel_graph = hotel_builder.compile()

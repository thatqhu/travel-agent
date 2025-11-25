import os
from typing import Literal
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
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
        "你是酒店搜索专家，负责根据用户的目的地、日期和预算查找合适的酒店选项。使用提供的工具搜索酒店信息。按距离,返回最近的2家即可."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    result = hotel_searcher.invoke(messages)
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
        "你是酒店评估专家，负责分析酒店的位置、设施、评价和性价比，给出一句话的总结."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    result = hotel_evaluator.invoke(messages)
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
        "你是酒店团队主管，协调 searcher(搜索酒店) 和 evaluator(评估酒店).先搜索再评估。完成后返回 FINISH。用简洁的中文回复."
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

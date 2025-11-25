import os
from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from pydantic import SecretStr
from agents.hotel_team import hotel_graph
from langchain.agents import create_agent
from langchain_community.tools.tavily_search import TavilySearchResults

api_key_val = os.environ.get("DASHSCOPE_API_KEY")
if not api_key_val:
    raise ValueError("DASHSCOPE_API_KEY is not set")
llm = ChatOpenAI(
    model="qwen-plus",
    api_key=SecretStr(api_key_val),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.5
)


class TravelState(MessagesState):
    next: str

itinerary_searcher = create_agent(
    llm
)


def call_hotel_team(state: TravelState) -> Command[Literal["supervisor"]]:
    """调用酒店团队"""
    response = hotel_graph.invoke({"messages": state["messages"]})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"🏨 [酒店团队完成]\n\n{response['messages'][-1].content}",
                    name="hotel_team"
                )
            ]
        },
        goto="supervisor"
    )

def call_itinerary_team(state: TravelState) -> Command[Literal["supervisor"]]:
    """调用行程团队"""
    system_prompt = (
        "你是行程设计师，负责设计完整的每日行程，包括交通、餐饮和预算规划。用专业且友好的语气, 简短总结一下."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = itinerary_searcher.invoke({"messages": messages})

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"🗓️ [行程团队完成]\n\n{response['messages'][-1].content}",
                    name="itinerary_team"
                )
            ]
        },
        goto="supervisor"
    )

def generate_final_plan(state: TravelState) -> Command[Literal["__end__"]]:
    """生成最终旅行计划"""
    messages = [
        {"role": "system", "content":
         "你是专业的旅行顾问。根据酒店团队和行程团队的工作结果，整合生成一份简短的旅行计划。用清晰的格式和友好的语气呈现."},
    ] + state["messages"]

    response = llm.invoke(messages)

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"✈️ [最终旅行计划]\n\n{response.content}",
                    name="final_planner"
                )
            ]
        },
        goto="__end__"
    )

def top_supervisor(state: TravelState) -> Command:
    """顶层监督者"""
    from typing_extensions import TypedDict

    class Router(TypedDict):
        next: Literal["hotel_team", "itinerary_team", "final_plan", "FINISH"]

    messages = [
        {"role": "system", "content":
         "你是旅行规划总监。协调 hotel_team(酒店搜索) 和 itinerary_team(行程规划)。"
         "工作流程：1. 先让hotel_team搜索酒店. 2. 然后让itinerary_team规划行程. "
         "3. 最后调用final_plan整合生成完整计划. 4. 没有结束返回json格式数据, 示例: {'next': 'hotel_team'}. 5. 返回FINISH结束。"},
    ] + state["messages"]

    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]

    if goto == "FINISH":
        goto = "__end__"

    return Command(goto=goto, update={"next": goto})

# 构建顶层图
travel_builder = StateGraph(TravelState)
travel_builder.add_node("supervisor", top_supervisor)
travel_builder.add_node("hotel_team", call_hotel_team)
travel_builder.add_node("itinerary_team", call_itinerary_team)
travel_builder.add_node("final_plan", generate_final_plan)
travel_builder.add_edge(START, "supervisor")
travel_graph = travel_builder.compile()

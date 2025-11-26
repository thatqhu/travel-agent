import os
from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from pydantic import SecretStr
from agents.hotel_team import hotel_graph
from langchain.agents import create_agent
from typing_extensions import TypedDict

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

class Router(TypedDict):
    next: Literal["hotel_team", "itinerary_team", "final_plan", "FINISH"]

def call_hotel_team(state: TravelState) -> Command[Literal["supervisor"]]:
    response = hotel_graph.invoke({"messages": state["messages"]})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"[酒店团队完成]\n{response['messages'][-1].content}",
                    name="hotel_team"
                )
            ]
        },
        goto="supervisor"
    )

def call_itinerary_team(state: TravelState) -> Command[Literal["supervisor"]]:
    # does not use subgraph here, just a simple call to LLM
    system_prompt = (
        "你是行程设计师，负责设计大概的每日行程,用专业且友好的语气, 简短总结一下,超过20个字."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = itinerary_searcher.invoke({"messages": messages})

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"[行程团队完成]\n{response['messages'][-1].content}\n",
                    name="itinerary_team"
                )
            ]
        },
        goto="supervisor"
    )

def generate_final_plan(state: TravelState) -> Command[Literal["__end__"]]:
    messages = [
        {"role": "system", "content":
         "你是专业的旅行顾问。根据酒店团队和行程团队的工作结果，整合生成一份简短的旅行计划。用清晰的格式和友好的语气呈现, 不超过50个字."},
    ] + state["messages"]

    response = llm.invoke(messages)

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"[最终旅行计划]\n{response.content}\n",
                    name="final_planner"
                )
            ]
        },
        goto="__end__"
    )

def top_supervisor(state: TravelState) -> Command:
    messages = [
        {"role": "system", "content":
         "你是旅行规划总监。协调 hotel_team(酒店搜索) 和 itinerary_team(行程规划)。"
         "工作流程：1. 先让hotel_team搜索酒店. 2. 然后让itinerary_team规划行程. "
         "3. 最后调用final_plan整合生成完整计划. 4. 完整计划生成前,返回json格式数据, 其中 next 字段指向下步操作 5. 返回FINISH结束。"},
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

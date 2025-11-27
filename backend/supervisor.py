import os
from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from pydantic import SecretStr
from agents.hotel_team import hotel_graph
from langchain.agents import create_agent

api_key_val = os.environ.get("DASHSCOPE_API_KEY")
if not api_key_val:
    raise ValueError("DASHSCOPE_API_KEY is not set")
llm = ChatOpenAI(
    model="qwen-plus",
    api_key=SecretStr(api_key_val),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    streaming=True,
    temperature=0.5
)


class TravelState(MessagesState):
    next: str

tool = TavilySearchResults(max_results=2)
itinerary_searcher = create_agent(
    llm,
    tools=[tool]
)

async def call_hotel_team(state: TravelState) -> Command[Literal["supervisor"]]:
    response = await hotel_graph.ainvoke({"messages": state["messages"]})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"\n**酒店团队完成**\n{response['messages'][-1].content}",
                    name="hotel_team"
                )
            ]
        }
    )

async def call_itinerary_team(state: TravelState) -> Command[Literal["supervisor"]]:
    # does not use subgraph here, just a simple call to LLM
    system_prompt = (
        "你是行程设计师，负责设计大概的每日行程,使用搜索工具查询最新的旅游攻略信息,用专业且友好的语气, 简短总结一下,超过20个字."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = await itinerary_searcher.ainvoke({"messages": messages})

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"\n**行程团队完成**\n{response['messages'][-1].content}\n",
                    name="itinerary_team"
                )
            ]
        }
    )

async def generate_final_plan(state: TravelState) -> Command[Literal["__end__"]]:
    messages = [
        {"role": "system", "content":
         "你是专业的旅行顾问。根据酒店团队和行程团队的工作结果，整合生成一份简短的旅行计划。用清晰的格式和友好的语气呈现, 不超过50个字."},
    ] + state["messages"]

    response = await llm.ainvoke(messages)

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=f"\n----最终旅行计划----\n{response.content}\n",
                    name="final_planner"
                )
            ]
        }
    )

async def top_supervisor(state: TravelState) -> Command:
    # Simple logic: If no team has worked yet, start both.
    # In a real agent, you might use llm to check state to see if they are ALL done.
    # Now, for testing purposes, we assume they can get the response in one go.
    # Here we assume a linear flow: Start -> (Hotel + Itinerary) -> Final

    last_message = state["messages"][-1]

    # If this is the first turn or user input, trigger parallel teams
    if not isinstance(last_message, HumanMessage) or last_message.name not in ["hotel_team", "itinerary_team"]:
         return Command(
             goto=["hotel_team", "itinerary_team"]
         )

    # Note: With the static edges we will add below, control won't actually
    # return to supervisor until final_plan is done (if we wire it that way),
    # or we can let final_plan go to END directly.

    return Command(goto="__end__")

# 构建顶层图
travel_builder = StateGraph(TravelState)
travel_builder.add_node("supervisor", top_supervisor)
travel_builder.add_node("hotel_team", call_hotel_team)
travel_builder.add_node("itinerary_team", call_itinerary_team)
travel_builder.add_node("final_plan", generate_final_plan)

# Start at supervisor
travel_builder.add_edge(START, "supervisor")

# Synchronization Run:
# This tells LangGraph: "Wait for BOTH hotel_team AND itinerary_team to finish, then run final_plan"
travel_builder.add_edge(["hotel_team", "itinerary_team"], "final_plan")

# End after plan
travel_builder.add_edge("final_plan", "__end__")

travel_graph = travel_builder.compile()

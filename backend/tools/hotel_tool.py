from typing import List, Optional
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader

tavily_tool = TavilySearch(max_results=1)

@tool
def search_hotels(destination: str) -> str:
    """
    搜索目的地的酒店信息

    Args:
        destination: 目的地城市
    """
    query = f"{destination} 酒店推荐, 只返回名字和地址"
    try:
        results = tavily_tool.invoke(query)
        return f"找到以下酒店信息：\n{results}"
    except Exception as e:
        return f"搜索酒店时出错: {str(e)}"

@tool
def evaluate_hotels(hotel_list: List[str], city: str) -> str:
    """
    评估并推荐酒店列表中的最佳选择

    Args:
        hotel_list: 酒店名称列表
        city: 所在城市
    """
    evaluations = []
    for hotel in hotel_list:
        query = f"{city} {hotel} 酒店 评价"
        try:
            result = tavily_tool.invoke(query)
            evaluations.append(f"{hotel} 评估：\n{result}")
        except Exception as e:
            evaluations.append(f"评估 {hotel} 时出错: {str(e)}")

    return "\n\n".join(evaluations)

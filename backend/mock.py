from langchain_core.tools import tool

@tool
def search_hotel(location: str, dates: str):
    """根据地点和日期搜索酒店"""
    return f"Mock Result: Found 3 hotels in {location} for {dates}: 1. Hilton ($200), 2. Marriott ($180), 3. Ibis ($100)."

@tool
def book_hotel(hotel_name: str, user_name: str):
    """预定指定酒店"""
    return f"Mock Result: Successfully booked {hotel_name} for {user_name}. Confirmation #12345."

@tool
def search_attractions(location: str):
    """搜索当地著名景点"""
    return f"Mock Result: Top attractions in {location}: The Grand Museum, City Park, Night Market."

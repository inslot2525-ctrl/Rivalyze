import os
import json
from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()


def _search(params: dict) -> str:
    params["api_key"] = os.getenv("SERPAPI_API_KEY")
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        for key in ["search_metadata", "search_parameters", "search_information"]:
            results.pop(key, None)
        return json.dumps(results, default=str)[:3000]
    except Exception as e:
        return json.dumps({"error": str(e)})


def web_search(company: str, query: str = None) -> str:
    q = query or f"{company} company overview"
    return _search({"engine": "google", "q": q, "num": 10})


def news_search(company: str, query: str = None) -> str:
    q = query or f"{company} latest news 2025"
    return _search({"engine": "google", "q": q, "tbm": "nws", "num": 10})


def shopping_search(company: str, query: str = None) -> str:
    q = query or f"{company} products pricing"
    return _search({"engine": "google", "q": q, "tbm": "shop", "num": 10})


def videos_search(company: str, query: str = None) -> str:
    q = query or company
    return _search({"engine": "youtube", "search_query": q, "num": 5})


def finance_search(company: str, query: str = None) -> str:
    q = query or f"{company} stock price market cap"
    return _search({"engine": "google", "q": q, "num": 5})


def jobs_search(company: str, query: str = None) -> str:
    q = query or f"{company} jobs hiring 2025"
    return _search({"engine": "google_jobs", "q": q})


def maps_search(company: str, query: str = None) -> str:
    q = query or f"{company} office headquarters"
    return _search({"engine": "google_maps", "q": q, "type": "search"})


def images_search(company: str, query: str = None) -> str:
    q = query or f"{company} company"
    return _search({"engine": "google", "q": q, "tbm": "isch", "num": 10})


def competitor_search(company: str) -> str:
    return _search({"engine": "google", "q": f"{company} competitors alternatives", "num": 10})


TOOL_MAP = {
    "web_search": web_search,
    "news_search": news_search,
    "shopping_search": shopping_search,
    "videos_search": videos_search,
    "finance_search": finance_search,
    "jobs_search": jobs_search,
    "maps_search": maps_search,
    "images_search": images_search,
    "competitor_search": competitor_search,
}


def make_tool(name, desc, params_schema):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": params_schema
        }
    }


BASE_PARAMS = {"type": "object", "properties": {"company": {"type": "string"}, "query": {"type": "string"}}, "required": ["company"]}
COMPETITOR_PARAMS = {"type": "object", "properties": {"company": {"type": "string"}}, "required": ["company"]}

TOOL_DEFINITIONS = [
    make_tool("web_search", "Search the web for general company information, overview, strategy, leadership", BASE_PARAMS),
    make_tool("news_search", "Search for recent news, announcements, press releases about a company", BASE_PARAMS),
    make_tool("shopping_search", "Search for product listings, pricing, marketplace presence", BASE_PARAMS),
    make_tool("videos_search", "Search YouTube for brand presence, product demos, interviews, reviews", BASE_PARAMS),
    make_tool("finance_search", "Search for stock price, market cap, financial metrics, earnings", BASE_PARAMS),
    make_tool("jobs_search", "Search for job postings as growth/contraction signal", BASE_PARAMS),
    make_tool("maps_search", "Search for physical office locations, headquarters, local presence", BASE_PARAMS),
    make_tool("images_search", "Search for visual brand signals, product images, media coverage", BASE_PARAMS),
    make_tool("competitor_search", "Identify key competitors and alternatives for a company", COMPETITOR_PARAMS),
]
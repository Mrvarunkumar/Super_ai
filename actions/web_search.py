from core import gemini

TOOL = {
    "name": "web_search",
    "description": "Search the web (Google-grounded) for current information: news, prices, facts, comparisons, research.",
    "parameters": {"type": "object", "properties": {
        "query": {"type": "string"},
        "mode": {"type": "string", "enum": ["search", "news", "price", "compare", "research"]}},
        "required": ["query"]},
}
PREFIX = {"search": "", "news": "Latest news on: ", "price": "Current price of: ",
          "compare": "Compare, with key differences: ", "research": "Research briefly: "}


def handler(params, ctx):
    mode = params.get("mode", "search")
    q = PREFIX.get(mode, "") + params["query"]
    try:
        return gemini.generate(q + "\n\nAnswer in under 120 words with the key facts and dates.", search=True, timeout=20)
    except Exception as e:
        return f"Search failed: {e}"

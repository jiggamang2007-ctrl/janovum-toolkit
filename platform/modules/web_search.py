"""
Janovum Module — Web Search
Searches the web and returns results for Claude to analyze.
Uses DuckDuckGo (free, no API key needed).

How it works:
  1. Client asks a question or module needs current info
  2. Python searches DuckDuckGo (free)
  3. Returns results to Claude for analysis
  4. Claude formats the answer
"""

import json
import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "web_search"
MODULE_DESC = "Web Search — search the internet, no API key needed"


def search(query, max_results=5):
    """
    Search DuckDuckGo and return results.
    Free, no API key needed.
    """
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    params = {"q": query}

    try:
        resp = requests.post(url, data=params, headers=headers, timeout=10)
        resp.raise_for_status()

        # Simple parsing of DuckDuckGo HTML results
        from html.parser import HTMLParser

        results = []

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_result = False
                self.in_title = False
                self.in_snippet = False
                self.current = {}

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                    self.in_title = True
                    self.current = {"title": "", "url": attrs_dict.get("href", ""), "snippet": ""}
                elif tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                    self.in_snippet = True

            def handle_endtag(self, tag):
                if tag == "a" and self.in_title:
                    self.in_title = False
                elif tag == "a" and self.in_snippet:
                    self.in_snippet = False
                    if self.current.get("title"):
                        results.append(self.current)
                    self.current = {}

            def handle_data(self, data):
                if self.in_title:
                    self.current["title"] += data.strip()
                elif self.in_snippet:
                    self.current["snippet"] += data.strip()

        parser = DDGParser()
        parser.feed(resp.text)

        return results[:max_results]

    except Exception as e:
        return [{"error": str(e)}]


def fetch_url(url):
    """Fetch a URL and return readable text content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        # Simple HTML to text
        import re
        text = resp.text
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return {"url": url, "text": text[:8000], "length": len(text)}

    except Exception as e:
        return {"error": str(e)}


# ── TOOL DEFINITIONS (for Claude agent loop) ──
TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for current information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {"type": "integer", "description": "Max results to return", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "web_fetch",
        "description": "Fetch a URL and extract readable text content",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"}
            },
            "required": ["url"]
        }
    }
]


def execute_tool(tool_name, tool_input):
    """Execute a web tool and return the result."""
    if tool_name == "web_search":
        return json.dumps(search(tool_input["query"], tool_input.get("max_results", 5)))
    elif tool_name == "web_fetch":
        return json.dumps(fetch_url(tool_input["url"]))
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


if __name__ == "__main__":
    results = search("best ROI real estate Miami 2026")
    for r in results:
        print(f"{r.get('title', 'N/A')}: {r.get('url', 'N/A')}")

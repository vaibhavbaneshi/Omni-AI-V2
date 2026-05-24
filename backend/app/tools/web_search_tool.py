from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import requests
from app.core.config import settings


class DuckDuckGoResultParser(HTMLParser):

    def __init__(self):

        super().__init__()
        self.results = []
        self.current_result = None
        self.current_field = None

    def handle_starttag(self, tag, attrs):

        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        if tag == "a" and "result__a" in class_name:

            href = attrs_dict.get("href", "")
            self.current_result = {
                "title": "",
                "url": clean_duckduckgo_url(href),
                "snippet": ""
            }
            self.current_field = "title"

        elif tag == "a" and "result__snippet" in class_name and self.current_result:

            self.current_field = "snippet"

    def handle_endtag(self, tag):

        if tag == "a" and self.current_result and self.current_field == "title":

            if self.current_result["title"] and self.current_result["url"]:
                self.results.append(self.current_result)

            self.current_result = None
            self.current_field = None

        elif tag == "a" and self.current_field == "snippet":

            self.current_field = None

    def handle_data(self, data):

        if not self.current_result or not self.current_field:
            return

        self.current_result[self.current_field] += data.strip() + " "


def clean_duckduckgo_url(url: str):

    if not url:
        return ""

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "uddg" in query:
        return unquote(query["uddg"][0])

    return url


def web_search_tool(query: str, max_results: int = 5):

    if settings.WEB_SEARCH_PROVIDER == "tavily" and settings.TAVILY_API_KEY:
        return tavily_search(query, max_results=max_results)

    if settings.WEB_SEARCH_PROVIDER == "serper" and settings.SERPER_API_KEY:
        return serper_search(query, max_results=max_results)

    return duckduckgo_search(query, max_results=max_results)


def tavily_search(query: str, max_results: int = 5):

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "max_results": max_results
            },
            timeout=12
        )
        response.raise_for_status()
        payload = response.json()

        sources = []
        for result in payload.get("results", []):
            url = result.get("url") or ""
            sources.append(
                {
                    "title": result.get("title") or url,
                    "source": urlparse(url).netloc.replace("www.", ""),
                    "url": url,
                    "chunk": result.get("content") or "",
                    "score": result.get("score"),
                    "strategy": "tavily-search",
                    "type": "web",
                    "metadata": {
                        "provider": "tavily",
                        "published_date": result.get("published_date")
                    }
                }
            )

        context = "\n\n".join(
            [
                f"[Web {index + 1}] {source['title']}\n{source['url']}\n{source['chunk']}"
                for index, source in enumerate(sources)
            ]
        )

        return {
            "context": context,
            "sources": sources,
            "status": "complete" if sources else "empty",
            "error": None if sources else "No Tavily results found",
            "provider": "tavily"
        }

    except Exception as error:
        return {
            "context": "",
            "sources": [],
            "status": "error",
            "error": str(error),
            "provider": "tavily"
        }


def serper_search(query: str, max_results: int = 5):

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "q": query,
                "num": max_results
            },
            timeout=12
        )
        response.raise_for_status()
        payload = response.json()

        sources = []
        for result in payload.get("organic", [])[:max_results]:
            url = result.get("link") or ""
            sources.append(
                {
                    "title": result.get("title") or url,
                    "source": urlparse(url).netloc.replace("www.", ""),
                    "url": url,
                    "chunk": result.get("snippet") or "",
                    "score": None,
                    "strategy": "serper-search",
                    "type": "web",
                    "metadata": {
                        "provider": "serper",
                        "date": result.get("date")
                    }
                }
            )

        context = "\n\n".join(
            [
                f"[Web {index + 1}] {source['title']}\n{source['url']}\n{source['chunk']}"
                for index, source in enumerate(sources)
            ]
        )

        return {
            "context": context,
            "sources": sources,
            "status": "complete" if sources else "empty",
            "error": None if sources else "No Serper results found",
            "provider": "serper"
        }

    except Exception as error:
        return {
            "context": "",
            "sources": [],
            "status": "error",
            "error": str(error),
            "provider": "serper"
        }


def duckduckgo_search(query: str, max_results: int = 5):

    try:

        response = requests.get(
            "https://duckduckgo.com/html/",
            params={
                "q": query
            },
            headers={
                "User-Agent": "OmniAI/1.0 (+https://localhost)"
            },
            timeout=8
        )

        response.raise_for_status()

        parser = DuckDuckGoResultParser()
        parser.feed(response.text)

        seen_urls = set()
        sources = []

        for result in parser.results:

            url = result["url"]

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            source = {
                "title": result["title"].strip(),
                "source": urlparse(url).netloc.replace("www.", ""),
                "url": url,
                "chunk": result["snippet"].strip() or result["title"].strip(),
                "score": None,
                "strategy": "web-search",
                "type": "web"
            }

            sources.append(source)

            if len(sources) >= max_results:
                break

        context = "\n\n".join(
            [
                f"[Web {index + 1}] {source['title']}\n{source['url']}\n{source['chunk']}"
                for index, source in enumerate(sources)
            ]
        )

        return {
            "context": context,
            "sources": sources,
            "status": "complete" if sources else "empty",
            "error": None if sources else "No web results found",
            "provider": "duckduckgo"
        }

    except Exception as error:

        return {
            "context": "",
            "sources": [],
            "status": "error",
            "error": str(error),
            "provider": "duckduckgo"
        }

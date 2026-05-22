#Defining the tools using tavily for reasearching
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool
import os

#Tavily tool - retrieves the top 5 search results with URLs and content
tavily_search = TavilySearchResults(max_results = 5, tavily_api_key = os.getenv("TAVILY_API_KEY"),
                                    include_answers = True, include_raw_content = False, )

#List of tools that are initialized
tools = [tavily_search]
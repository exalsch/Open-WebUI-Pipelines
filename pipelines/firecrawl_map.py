"""
title: Firecrawl URL Mapping
author: Ademílson Tonato (@ftonato) - Mendable
author_url: https://github.com/mendableai
git_url: https://github.com/mendableai/open-webui-pipelines/blob/main/pipelines/firecrawl_map.py
description: URL mapping and discovery using Firecrawl API
required_open_webui_version: 0.4.3
requirements: requests
version: 1.0.0
licence: MIT
"""

import os
import json
import requests
import re
import traceback
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field
from logging import getLogger

logger = getLogger(__name__)
logger.setLevel("DEBUG")

# Request and Response Models
class MapRequest(BaseModel):
    url: str
    search: str = ""
    ignoreSitemap: bool = False
    sitemapOnly: bool = False
    includeSubdomains: bool = False
    limit: int = 1000
    
class MapResponse(BaseModel):
    success: bool
    links: List[str]

class FirecrawlClient:
    def __init__(self, api_key: str, debug: bool = False):
        self.api_key = api_key
        self.base_url = "https://api.firecrawl.dev/v1"
        self.debug = debug

    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Origin": "openwebui",
            "X-Origin-Type": "integration",
        }

    def map_urls(self, request: MapRequest) -> MapResponse:
        endpoint = "/map"
        url = f"{self.base_url}{endpoint}"
        headers = self.headers()
        
        if self.debug:
            logger.debug(f"Map request: {json.dumps(request.model_dump(), indent=2)}")
            logger.debug(f"Endpoint: {url}")
            logger.debug(f"Using API key: {self.api_key[:4]}...{self.api_key[-4:] if len(self.api_key) > 8 else ''}")
        
        try:
            payload = {
                "url": request.url,
                "search": request.search,
                "ignoreSitemap": request.ignoreSitemap,
                "sitemapOnly": request.sitemapOnly,
                "includeSubdomains": request.includeSubdomains,
                "limit": request.limit
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if self.debug:
                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            response_data = response.json()
            if self.debug:
                logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
            
            return MapResponse(**response_data)
        except requests.exceptions.RequestException as e:
            if self.debug:
                logger.error(f"Request failed: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                logger.error(traceback.format_exc())
            raise Exception(f"Request failed: {e}")

class Pipeline:
    class Valves(BaseModel):
        FIRECRAWL_API_KEY: str = Field(default="", description="Firecrawl API key")
        URL_LIMIT: int = Field(default=100, description="Maximum number of URLs to process")
        IGNORE_SITEMAP: bool = Field(default=False, description="Ignore sitemap.xml when mapping URLs")
        SITEMAP_ONLY: bool = Field(default=False, description="Only use sitemap.xml when mapping URLs")
        INCLUDE_SUBDOMAINS: bool = Field(default=False, description="Include subdomains when mapping URLs")
    
    def __init__(self):
        self.name = "Firecrawl URL Mapping Pipeline"
        
        # Private debug flag for development only
        self._debug = False
        
        # Initialize valve parameters
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )

        # let's print all the valves with a prefix so we know which ones are set
        for k, v in self.valves.model_dump().items():
            logger.debug(f"Valve item: {k}")
            if v:
                logger.debug(f"{k}: {v}")
            else:
                logger.debug(f"{k}: not set")

        
        if self._debug:
            logger.debug(f"Initialized {self.name} with valves: {self.valves.model_dump()}")
            api_key = self.valves.FIRECRAWL_API_KEY
            logger.debug(f"Using API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    
    async def on_startup(self):
        logger.debug(f"on_startup:{self.name}")
        if not self.valves.FIRECRAWL_API_KEY:
            logger.warning("FIRECRAWL_API_KEY not set. Pipeline will not function correctly.")
        
        if self._debug:
            logger.debug("Debug mode is enabled. Detailed logs will be shown.")
    
    async def on_shutdown(self):
        logger.debug(f"on_shutdown:{self.name}")
    
    def _extract_url_from_message(self, message: str) -> str:
        # Initialize the Firecrawl client
        self.client = FirecrawlClient(api_key=self.valves.FIRECRAWL_API_KEY, debug=self._debug)

        """Extract URL from user message"""
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, message)
        
        if self._debug:
            logger.debug(f"Extracted URLs from message: {urls}")
        
        return urls[0] if urls else None
    
    def _extract_search_term(self, message: str) -> str:
        """Extract search term from user message if present"""
        search_patterns = [
            r'search for "(.*?)"',
            r'search "(.*?)"',
            r'find "(.*?)"',
            r'containing "(.*?)"',
            r'with "(.*?)"',
            r'include "(.*?)"',
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                search_term = match.group(1)
                if self._debug:
                    logger.debug(f"Extracted search term: {search_term}")
                return search_term
        
        if self._debug:
            logger.debug("No search term found in message")
        
        return ""
    
    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Process the user message and perform map operation using Firecrawl API
        """
        logger.debug(f"pipe:{__name__}")
        
        if self._debug:
            logger.debug(f"User message: {user_message}")
            logger.debug(f"Model ID: {model_id}")
            logger.debug(f"Body: {json.dumps(body, indent=2)}")
        
        if body.get("title", False):
            return "Firecrawl URL Mapping Pipeline"
        
        # Check if API key is set
        if not self.valves.FIRECRAWL_API_KEY:
            return "Error: FIRECRAWL_API_KEY not set. Please set it in your environment variables."
    
        logger.debug(f"FIRECRAWL_API_KEY: {self.valves.FIRECRAWL_API_KEY}")
        
        # Check if debug command is in the message - only for development
        if "debug on" in user_message.lower():
            self._debug = True
            if hasattr(self, 'client'):
                self.client.debug = True
            logger.debug("Debug mode enabled")
            return "Debug mode has been enabled. Detailed logs will now be shown."
        
        if "debug off" in user_message.lower():
            self._debug = False
            if hasattr(self, 'client'):
                self.client.debug = False
            logger.debug("Debug mode disabled")
            return "Debug mode has been disabled."
        
        if "debug status" in user_message.lower():
            status = "enabled" if self._debug else "disabled"
            return f"Debug mode is currently {status}."
        
        # Extract URL from user message
        url = self._extract_url_from_message(user_message)
        if not url:
            return "No URL found in your message. Please provide a valid URL to map."
        
        # Extract search term if present
        search_term = self._extract_search_term(user_message)
        
        # Perform map operation
        try:
            request = MapRequest(
                url=url,
                search=search_term,
                ignoreSitemap=self.valves.IGNORE_SITEMAP,
                sitemapOnly=self.valves.SITEMAP_ONLY,
                includeSubdomains=self.valves.INCLUDE_SUBDOMAINS,
                limit=self.valves.URL_LIMIT
            )
            
            if self._debug:
                logger.debug(f"Created map request: {request.model_dump()}")
            
            response = self.client.map_urls(request)
            
            if self._debug:
                logger.debug(f"Received map response with {len(response.links)} URLs")
                logger.debug(f"First 5 URLs: {response.links[:5] if len(response.links) >= 5 else response.links}")
            
            # if there's no search term, just show
            if not search_term:
                result = f"Found {len(response.links)} URLs on {url}."
            else:
                result = f"Found {len(response.links)} URLs on {url} containing '{search_term}'."
                
            result += "\n\nList of mapped URLs:"
            if not response.links:
                result += "\nNothing was found []"
            else:
                result += "\n" + "\n".join(f"- {url}" for url in response.links)
            return result
        except Exception as e:
            error_msg = f"Error during map operation: {str(e)}"
            logger.error(error_msg)
            
            if self._debug:
                logger.error(traceback.format_exc())
                return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
            
            return error_msg
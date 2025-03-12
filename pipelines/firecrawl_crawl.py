"""
title: Firecrawl Web Crawling
author: Ademílson Tonato (@ftonato) - Mendable
author_url: https://github.com/mendableai
git_url: https://github.com/mendableai/open-webui-pipelines/blob/main/pipelines/firecrawl_crawl.py
description: Web crawling and content extraction using Firecrawl API
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
from typing import List, Dict, Any, Union, Generator, Iterator
from pydantic import BaseModel, Field
from logging import getLogger

logger = getLogger(__name__)
logger.setLevel("DEBUG")

# Request and Response Models
class CrawlRequest(BaseModel):
    url: str
    excludePaths: List[str] = Field(default_factory=list)
    includePaths: List[str] = Field(default_factory=list)
    maxDepth: int = 3
    ignoreSitemap: bool = False
    ignoreQueryParameters: bool = False
    limit: int = 500
    allowBackwardLinks: bool = False
    allowExternalLinks: bool = False
    scrapeOptions: Dict[str, Any] = Field(default_factory=dict)
    
class CrawlResponse(BaseModel):
    id: str
    success: bool
    url: str | None = None

class CrawlStatusRequest(BaseModel):
    id: str
    
class CrawlStatusResponse(BaseModel):
    status: str
    total: int = 0
    completed: int = 0
    creditsUsed: int = 0
    expiresAt: str | None = None
    next: str | None = None
    data: List[Dict[str, Any]] = Field(default_factory=list)
    error: str | None = None  # For error responses

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

    def crawl_urls(self, request: CrawlRequest) -> CrawlResponse:
        endpoint = "/crawl"
        url = f"{self.base_url}{endpoint}"
        headers = self.headers()
        
        if self.debug:
            logger.debug(f"Crawl request: {json.dumps(request.model_dump(), indent=2)}")
            logger.debug(f"Endpoint: {url}")
            logger.debug(f"Using API key: {self.api_key[:4]}...{self.api_key[-4:] if len(self.api_key) > 8 else ''}")
        
        try:
            # Convert the request to a dictionary and then to JSON for better control
            payload = request.model_dump()
            
            if self.debug:
                logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, headers=headers)
            
            if self.debug:
                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content: {response.text}")
            
            # Handle 400 errors with more detailed information
            if response.status_code == 400:
                error_detail = "Unknown error"
                try:
                    error_data = response.json()
                    error_detail = json.dumps(error_data, indent=2)
                except:
                    error_detail = response.text
                
                logger.error(f"400 Bad Request Error: {error_detail}")
                raise Exception(f"API returned 400 Bad Request: {error_detail}")
            
            response.raise_for_status()
            
            response_data = response.json()
            if self.debug:
                logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
            
            return CrawlResponse(**response_data)
        except requests.exceptions.RequestException as e:
            if self.debug:
                logger.error(f"Request failed: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                    
                    # Try to parse the error response as JSON for more details
                    try:
                        error_json = e.response.json()
                        logger.error(f"Error details: {json.dumps(error_json, indent=2)}")
                    except:
                        pass
                        
                logger.error(traceback.format_exc())
            raise Exception(f"Request failed: {e}")
  
    def get_crawl_status(self, request: CrawlStatusRequest) -> CrawlStatusResponse:
        endpoint = f"/crawl/{request.id}"
        url = f"{self.base_url}{endpoint}"
        headers = self.headers()
        
        if self.debug:
            logger.debug(f"Crawl status request for ID: {request.id}")
            logger.debug(f"Endpoint: {url}")
            logger.debug(f"Using API key: {self.api_key[:4]}...{self.api_key[-4:] if len(self.api_key) > 8 else ''}")
        
        try:
            response = requests.get(url, headers=headers)
            
            if self.debug:
                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content: {response.text}")
            
            # Handle error responses (402, 429, 500)
            if response.status_code in [402, 429, 500]:
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", "Unknown error")
                    return CrawlStatusResponse(status="error", error=error_message)
                except:
                    return CrawlStatusResponse(status="error", error=f"Error {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            response_data = response.json()
            if self.debug:
                logger.debug(f"Response data summary: Status: {response_data.get('status')}, Total: {response_data.get('total')}, Completed: {response_data.get('completed')}")
                if 'data' in response_data:
                    logger.debug(f"Data items: {len(response_data.get('data', []))}")
            
            return CrawlStatusResponse(**response_data)
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
        DEFAULT_FORMAT: str = Field(default="markdown", description="Default format for content extraction")
        ONLY_MAIN_CONTENT: bool = Field(default=True, description="Extract only main content")
        WAIT_FOR: int = Field(default=5000, description="Wait time in milliseconds")
        MAX_DEPTH: int = Field(default=3, description="Maximum crawl depth")
        URL_LIMIT: int = Field(default=100, description="Maximum number of URLs to process")
        INCLUDE_PATHS: str = Field(default="", description="Comma-separated list of paths to include")
        EXCLUDE_PATHS: str = Field(default="", description="Comma-separated list of paths to exclude")
        IGNORE_SITEMAP: bool = Field(default=False, description="Ignore sitemap.xml when crawling")
        IGNORE_QUERY_PARAMS: bool = Field(default=False, description="Ignore query parameters in URLs")
        ALLOW_BACKWARD_LINKS: bool = Field(default=False, description="Allow backward links during crawling")
        ALLOW_EXTERNAL_LINKS: bool = Field(default=False, description="Allow external links during crawling")
        BLOCK_ADS: bool = Field(default=True, description="Block ads during crawling")
        REMOVE_BASE64_IMAGES: bool = Field(default=True, description="Remove base64 encoded images from content")
        MOBILE: bool = Field(default=False, description="Use mobile user agent")
        TIMEOUT: int = Field(default=30000, description="Request timeout in milliseconds")
    
    def __init__(self):
        self.name = "Firecrawl Web Crawling Pipeline"
        
        # Private debug flag for development only
        self._debug = False
        
        # Initialize valve parameters
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        
        if self._debug:
            logger.debug(f"Initialized {self.name} with valves: {self.valves.model_dump()}")
            if not self.valves.FIRECRAWL_API_KEY:
                logger.warning("FIRECRAWL_API_KEY is not set or empty")
            else:
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
    
    def _extract_crawl_id(self, message: str) -> str:
        """Extract crawl ID from user message if present"""
        id_patterns = [
            r'status of ([\w-]+)',
            r'check ([\w-]+)',
            r'crawl ([\w-]+)',
            r'id ([\w-]+)',
            r'job ([\w-]+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                crawl_id = match.group(1)
                if self._debug:
                    logger.debug(f"Extracted crawl ID: {crawl_id}")
                return crawl_id
        
        if self._debug:
            logger.debug("No crawl ID found in message")
        
        return None
    
    def _parse_path_list(self, paths_str: str) -> List[str]:
        """Parse comma-separated path list into a list of strings"""
        if not paths_str or paths_str.strip() == "":
            return []
        
        paths = [p.strip() for p in paths_str.split(',') if p.strip()]
        
        if self._debug:
            logger.debug(f"Parsed path list: {paths}")
        
        return paths
    
    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Process the user message and perform crawl operation using Firecrawl API
        """
        logger.debug(f"pipe:{__name__}")
        
        if self._debug:
            logger.debug(f"User message: {user_message}")
            logger.debug(f"Model ID: {model_id}")
            logger.debug(f"Body: {json.dumps(body, indent=2)}")
        
        if body.get("title", False):
            return "Firecrawl Web Crawling Pipeline"
            
        # Check if this is the first message (empty or just contains a greeting)
        greeting_patterns = [
            r'^hi$', r'^hello$', r'^hey$', r'^start$', r'^begin$', r'^help$',
            r'^hi\s', r'^hello\s', r'^hey\s', r'^start\s', r'^begin\s', r'^help\s'
        ]
        
        is_greeting = not user_message or any(re.search(pattern, user_message.lower()) for pattern in greeting_patterns)
        
        if not user_message or is_greeting:
            welcome_msg = "👋 Hello! Welcome to the Firecrawl Web Crawling Pipeline.\n\n"
            welcome_msg += "You can type the URL of a website you want to crawl, and I'll extract its content for you.\n\n"
            welcome_msg += "For example: https://example.com\n\n"
            welcome_msg += "To check the status of a previous crawl job, type: check status of [job-id]\n\n"
            welcome_msg += "Happy crawling! 🕸️"
            return welcome_msg
        
        # Check if API key is set
        if not self.valves.FIRECRAWL_API_KEY:
            return "Error: FIRECRAWL_API_KEY not set. Please set it in your environment variables."
        
        # Check if API key command is in the message
        if "set api key" in user_message.lower():
            # Extract API key from message
            api_key_pattern = r'set api key[:\s]+([a-zA-Z0-9_\-]+)'
            match = re.search(api_key_pattern, user_message, re.IGNORECASE)
            if match:
                new_api_key = match.group(1)
                self.valves.FIRECRAWL_API_KEY = new_api_key
                self.client.api_key = new_api_key
                logger.info("API key updated")
                return f"API key has been updated. First 4 characters: {new_api_key[:4]}..."
            else:
                return "Could not extract API key from message. Format should be: set api key YOUR_API_KEY"
        
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
        
        # Check if user is requesting crawl status
        crawl_id = self._extract_crawl_id(user_message)
        if crawl_id and ("status" in user_message.lower() or "check" in user_message.lower()):
            try:
                if self._debug:
                    logger.debug(f"Checking status for crawl ID: {crawl_id}")
                
                request = CrawlStatusRequest(id=crawl_id)
                response = self.client.get_crawl_status(request)
                
                if self._debug:
                    logger.debug(f"Crawl status response: {response.model_dump()}")
                
                # Check if there was an error
                if response.error:
                    return f"Error getting crawl status: {response.error}"
                
                # Build status message with the new response format
                status_msg = f"Crawl job status: {response.status}\n\n"
                status_msg += f"Total URLs: {response.total}\n"
                status_msg += f"Completed: {response.completed}\n"
                status_msg += f"Credits used: {response.creditsUsed}\n"
                
                if response.expiresAt:
                    status_msg += f"Expires at: {response.expiresAt}\n"
                
                # Show sample of completed URLs if available
                if response.data and len(response.data) > 0:
                    status_msg += "\nList of all crawled pages:\n"
                    for i, item in enumerate(response.data):
                        url = item.get("metadata", {}).get("sourceURL", "Unknown URL")
                        title = item.get("metadata", {}).get("title", "No title")
                        status_msg += f"{i+1}. {title} - {url}\n"
                
                return status_msg
            except Exception as e:
                error_msg = f"Error getting crawl status: {str(e)}"
                logger.error(error_msg)
                
                if self._debug:
                    logger.error(traceback.format_exc())
                    return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
                
                return error_msg
        
        # Extract URL from user message for new crawl
        url = self._extract_url_from_message(user_message)
        if not url:
            return "No URL found in your message. Please provide a valid URL to crawl or a crawl ID to check status."
        
        # Perform crawl operation
        try:
            # Parse include and exclude paths
            include_paths = self._parse_path_list(self.valves.INCLUDE_PATHS)
            exclude_paths = self._parse_path_list(self.valves.EXCLUDE_PATHS)
            
            if self._debug:
                logger.debug(f"Include paths: {include_paths}")
                logger.debug(f"Exclude paths: {exclude_paths}")
            
            # Build scrape options
            scrape_options = {
                "formats": [self.valves.DEFAULT_FORMAT],
                "onlyMainContent": self.valves.ONLY_MAIN_CONTENT,
                "waitFor": self.valves.WAIT_FOR,
                "mobile": self.valves.MOBILE,
                "timeout": self.valves.TIMEOUT,
                "removeBase64Images": self.valves.REMOVE_BASE64_IMAGES,
                "blockAds": self.valves.BLOCK_ADS
            }
            
            # Create request with default values
            request_data = {
                "url": url,
                "maxDepth": self.valves.MAX_DEPTH,
                "limit": self.valves.URL_LIMIT,
                "ignoreSitemap": self.valves.IGNORE_SITEMAP,
                "ignoreQueryParameters": self.valves.IGNORE_QUERY_PARAMS,
                "allowBackwardLinks": self.valves.ALLOW_BACKWARD_LINKS,
                "allowExternalLinks": self.valves.ALLOW_EXTERNAL_LINKS,
                "scrapeOptions": scrape_options
            }
            
            # Only add include/exclude paths if they're not empty
            if include_paths:
                request_data["includePaths"] = include_paths
            
            if exclude_paths:
                request_data["excludePaths"] = exclude_paths
            
            # For debugging, show the exact request that will be sent
            if self._debug:
                logger.debug(f"Raw request data: {json.dumps(request_data, indent=2)}")
            
            request = CrawlRequest(**request_data)
            
            if self._debug:
                logger.debug(f"Created crawl request: {request.model_dump()}")
            
            response = self.client.crawl_urls(request)
            
            if self._debug:
                logger.debug(f"Received crawl response: {response.model_dump()}")
            
            # Updated response message to use the correct attributes
            success_status = "successful" if response.success else "failed"
            return (f"Crawl job started with ID: {response.id}. Status: {success_status}\n\n"
                   f"To check the status later, ask: 'Check status of {response.id}'")
        except Exception as e:
            error_msg = f"Error during crawl operation: {str(e)}"
            logger.error(error_msg)
            
            if self._debug:
                logger.error(traceback.format_exc())
                return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
            
            return error_msg 
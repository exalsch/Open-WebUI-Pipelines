"""
title: Firecrawl Web Scraping
author: Ademílson Tonato (@ftonato) - Mendable
author_url: https://github.com/mendableai
git_url: https://github.com/mendableai/open-webui-pipelines/blob/main/pipelines/firecrawl_scrape.py
description: Web scraping and data extraction using Firecrawl API
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
class ScrapeRequest(BaseModel):
    url: str
    formats: List[str] = Field(default_factory=lambda: ["markdown"])
    onlyMainContent: bool = True
    includeTags: List[str] = Field(default_factory=list)
    excludeTags: List[str] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    waitFor: int = 5000
    mobile: bool = False
    skipTlsVerification: bool = False
    timeout: int = 30000
    # jsonOptions: Dict[str, Any] = Field(default_factory=dict)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    location: Dict[str, Any] = Field(default_factory=dict)
    removeBase64Images: bool = True
    blockAds: bool = True
    proxy: str = ""

class ScrapeResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

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

    def scrape_and_extract_from_url(self, request: ScrapeRequest) -> ScrapeResponse:
        endpoint = "/scrape"
        url = f"{self.base_url}{endpoint}"
        headers = self.headers()
        
        if self.debug:
            logger.debug(f"Scrape request: {json.dumps(request.model_dump(), indent=2)}")
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
            
            # Handle error responses (402, 429, 500)
            if response.status_code in [402, 429, 500]:
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", "Unknown error")
                    return ScrapeResponse(success=False, error=error_message)
                except:
                    return ScrapeResponse(success=False, error=f"Error {response.status_code}: {response.text}")
            
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
            
            return ScrapeResponse(**response_data)
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

class Pipe:
    class Valves(BaseModel):
        FIRECRAWL_API_KEY: str = Field(default="", description="Firecrawl API key")
        FORMATS: str = Field(default="markdown", description="Comma-separated list of formats to scrape")
        ONLY_MAIN_CONTENT: bool = Field(default=True, description="Extract only main content")
        INCLUDE_TAGS: str = Field(default="", description="Comma-separated list of tags to include")
        EXCLUDE_TAGS: str = Field(default="", description="Comma-separated list of tags to exclude")
        HEADERS: str = Field(default="", description="Object of headers to send with the request")
        WAIT_FOR: int = Field(default=5000, description="Wait time in milliseconds")
        MOBILE: bool = Field(default=False, description="Use mobile user agent")
        TIMEOUT: int = Field(default=30000, description="Request timeout in milliseconds")
        BLOCK_ADS: bool = Field(default=True, description="Block ads during scraping")
        REMOVE_BASE64_IMAGES: bool = Field(default=True, description="Remove base64 encoded images from content")
        PROXY: str = Field(default="basic", description="Proxy for scraping (basic or stealth)")
        LOCATION_COUNTRY: str = Field(default="US", description="Country for location-based scraping")
        LOCATION_LANGUAGES: str = Field(default="en-US", description="Comma-separated list of languages to scrape")
        ACTIONS: str = Field(default="", description="Comma-separated list of actions to perform. Eg. ({ 'type': 'wait', 'milliseconds': 2, 'selector': '#my-element' }, { 'type': 'wait', 'milliseconds': 10, 'selector': '#my-other-element' })")
        # JSON_OPTIONS: str = Field(default="", description="Object of JSON options to send with the request")
    
    def __init__(self):
        self.name = "Firecrawl Web Scraping Pipeline"
        
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
    
    def _format_scrape_result(self, result: Dict[str, Any], format_type: str = "markdown") -> str:
        """Format the scrape result for display"""
        if self._debug:
            logger.debug(f"Formatting result for format: {format_type}")
            logger.debug(f"Result keys: {result.keys() if result else None}")
        
        if not result or not result.get("data"):
            return "No content was extracted from the URL."
        
        data = result["data"]
        
        if not data.get(format_type):
            return "No content was extracted in the requested format."
        
        content = data[format_type]
        
        # Build a formatted response
        response = f"### Extracted Content\n\n{content}\n\n"
        
        # Add metadata if available
        if data.get("metadata"):
            metadata = data["metadata"]
            response += "### Metadata\n\n"
            
            if metadata.get("title"):
                response += f"**Title:** {metadata['title']}\n\n"
            
            if metadata.get("description"):
                response += f"**Description:** {metadata['description']}\n\n"
            
            if metadata.get("language"):
                response += f"**Language:** {metadata['language']}\n\n"
        
        # Add links if available
        if data.get("links") and len(data["links"]) > 0:
            response += "### Links Found\n\n"
            for i, link in enumerate(data["links"]):
                response += f"{i+1}. {link}\n"
        
        # Add warning if present
        if data.get("warning"):
            response += f"\n⚠️ **Warning:** {data['warning']}\n"
        
        return response
    
    def _parse_tag_list(self, tags_str: str) -> List[str]:
        """Parse comma-separated tag list into a list of strings"""
        if not tags_str or tags_str.strip() == "":
            return []
        
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        
        if self._debug:
            logger.debug(f"Parsed tag list: {tags}")
        
        return tags
    
    def _parse_formats(self, formats_str: str) -> List[str]:
        """Parse comma-separated formats into a list of strings"""
        if not formats_str or formats_str.strip() == "":
            return ["markdown"]  # Default format
        
        formats = [f.strip() for f in formats_str.split(',') if f.strip()]
        
        if self._debug:
            logger.debug(f"Parsed formats: {formats}")
        
        return formats
    
    def _parse_headers(self, headers_str: str) -> Dict[str, str]:
        """Parse headers string into a dictionary"""
        if not headers_str or headers_str.strip() == "":
            return {}
        
        try:
            headers = json.loads(headers_str)
            if self._debug:
                logger.debug(f"Parsed headers: {headers}")
            return headers
        except json.JSONDecodeError:
            logger.error(f"Failed to parse headers JSON: {headers_str}")
            return {}
    
    def _parse_location(self, country: str, languages_str: str) -> Dict[str, Any]:
        """Parse location information into a dictionary"""
        location = {}
        
        if country and country.strip():
            location["country"] = country.strip()
        
        if languages_str and languages_str.strip():
            languages = [lang.strip() for lang in languages_str.split(',') if lang.strip()]
            if languages:
                location["languages"] = languages
        
        if self._debug:
            logger.debug(f"Parsed location: {location}")
        
        return location
    
    def _parse_actions(self, actions_str: str) -> List[Dict[str, Any]]:
        """Parse actions string into a list of dictionaries"""
        if not actions_str or actions_str.strip() == "":
            return []
        
        try:
            actions = json.loads(actions_str)
            if isinstance(actions, list):
                if self._debug:
                    logger.debug(f"Parsed actions: {actions}")
                return actions
            else:
                logger.error(f"Actions must be a list, got: {type(actions)}")
                return []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse actions JSON: {actions_str}")
            return []

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Process the user message and perform scrape operation using Firecrawl API
        """
        logger.debug(f"pipe:{__name__}")
        
        if self._debug:
            logger.debug(f"User message: {user_message}")
            logger.debug(f"Model ID: {model_id}")
            logger.debug(f"Body: {json.dumps(body, indent=2)}")
        
        if body.get("title", False):
            return "Firecrawl Web Scraping Pipeline"
            
        # Check if this is the first message (empty or just contains a greeting)
        greeting_patterns = [
            r'^hi$', r'^hello$', r'^hey$', r'^start$', r'^begin$', r'^help$',
            r'^hi\s', r'^hello\s', r'^hey\s', r'^start\s', r'^begin\s', r'^help\s'
        ]
        
        is_greeting = not user_message or any(re.search(pattern, user_message.lower()) for pattern in greeting_patterns)
        
        if not user_message or is_greeting:
            welcome_msg = "👋 Hello! Welcome to the Firecrawl Web Scraping Pipeline.\n\n"
            welcome_msg += "You can type the URL of a website you want to scrape, and I'll extract its content for you.\n\n"
            welcome_msg += "For example: https://example.com\n\n"
            welcome_msg += "Happy scraping! 🕸️"
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
            self.client.debug = True
            logger.debug("Debug mode enabled")
            return "Debug mode has been enabled. Detailed logs will now be shown."
        
        if "debug off" in user_message.lower():
            self._debug = False
            self.client.debug = False
            logger.debug("Debug mode disabled")
            return "Debug mode has been disabled."
        
        if "debug status" in user_message.lower():
            status = "enabled" if self._debug else "disabled"
            return f"Debug mode is currently {status}."
        
        # Extract URL from user message
        url = self._extract_url_from_message(user_message)
        if not url:
            return "No URL found in your message. Please provide a valid URL to scrape."
        
        # Perform scrape operation
        try:
            # Parse all the valve parameters
            formats = self._parse_formats(self.valves.FORMATS)
            include_tags = self._parse_tag_list(self.valves.INCLUDE_TAGS)
            exclude_tags = self._parse_tag_list(self.valves.EXCLUDE_TAGS)
            headers = self._parse_headers(self.valves.HEADERS)
            actions = self._parse_actions(self.valves.ACTIONS)
            location = self._parse_location(self.valves.LOCATION_COUNTRY, self.valves.LOCATION_LANGUAGES)

            if self._debug:
                logger.debug(f"Formats: {formats}")
                logger.debug(f"Include tags: {include_tags}")
                logger.debug(f"Exclude tags: {exclude_tags}")
                logger.debug(f"Headers: {headers}")
                logger.debug(f"Actions: {actions}")
                logger.debug(f"Location: {location}")

            # Create request with all parameters
            request_data = {
                "url": url,
                "formats": formats,
                "onlyMainContent": self.valves.ONLY_MAIN_CONTENT,
                "waitFor": self.valves.WAIT_FOR,
                "mobile": self.valves.MOBILE,
                "timeout": self.valves.TIMEOUT,
                "skipTlsVerification": False,  # Default value
                "removeBase64Images": self.valves.REMOVE_BASE64_IMAGES,
                "blockAds": self.valves.BLOCK_ADS
            }
            
            # Only add optional parameters if they're not empty
            if include_tags:
                request_data["includeTags"] = include_tags
            
            if exclude_tags:
                request_data["excludeTags"] = exclude_tags
                
            if headers:
                request_data["headers"] = headers
                
            if actions:
                request_data["actions"] = actions
                
            if location:
                request_data["location"] = location
                
            if self.valves.PROXY:
                request_data["proxy"] = self.valves.PROXY

            # For debugging, show the exact request that will be sent
            if self._debug:
                logger.debug(f"Raw request data: {json.dumps(request_data, indent=2)}")
            
            request = ScrapeRequest(**request_data)
            
            if self._debug:
                logger.debug(f"Created scrape request: {request.model_dump()}")
            
            response = self.client.scrape_and_extract_from_url(request)
            
            if self._debug:
                logger.debug(f"Received scrape response: {response.model_dump()}")
            
            # Check if there was an error
            if response.error:
                return f"Error during scrape operation: {response.error}"
            
            return self._format_scrape_result(response.model_dump(), formats[0] if formats else "markdown")
        except Exception as e:
            error_msg = f"Error during scrape operation: {str(e)}"
            logger.error(error_msg)
            
            if self._debug:
                logger.error(traceback.format_exc())
                return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
            
            return error_msg

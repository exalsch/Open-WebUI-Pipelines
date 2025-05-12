"""
title: Firecrawl Data Extraction
author: Ademílson Tonato (@ftonato) - Mendable
author_url: https://github.com/mendableai
git_url: https://github.com/mendableai/open-webui-pipelines/blob/main/pipelines/firecrawl_extract.py
description: Structured data extraction from websites using Firecrawl API
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
class ExtractRequest(BaseModel):
    urls: List[str]
    prompt: str
    schema: Dict[str, Any] = Field(default_factory=dict)
    enableWebSearch: bool = False
    ignoreSitemap: bool = False
    includeSubdomains: bool = False
    showSources: bool = False
    scrapeOptions: Dict[str, Any] = Field(default_factory=dict)

class ExtractResponse(BaseModel):
    success: bool
    id: str

class ExtractStatusRequest(BaseModel):
    id: str
    
class ExtractStatusResponse(BaseModel):
    success: bool
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(default_factory=dict)
    status: str
    expiresAt: str | None = None
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

    def extract_data(self, request: ExtractRequest) -> ExtractResponse:
        endpoint = "/extract"
        url = f"{self.base_url}{endpoint}"
        headers = self.headers()
        
        if self.debug:
            logger.debug(f"Extract request: {json.dumps(request.model_dump(), indent=2)}")
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
                    raise Exception(f"API error: {error_message}")
                except json.JSONDecodeError:
                    raise Exception(f"Error {response.status_code}: {response.text}")
            
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
            
            return ExtractResponse(**response_data)
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
  
    def get_extract_status(self, request: ExtractStatusRequest) -> ExtractStatusResponse:
        endpoint = f"/extract/{request.id}"
        url = f"{self.base_url}{endpoint}"
        headers = self.headers()
        
        if self.debug:
            logger.debug(f"Extract status request for ID: {request.id}")
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
                    return ExtractStatusResponse(success=False, status="error", error=error_message)
                except:
                    return ExtractStatusResponse(success=False, status="error", error=f"Error {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            response_data = response.json()
            if self.debug:
                logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
            
            return ExtractStatusResponse(**response_data)
        except requests.exceptions.RequestException as e:
            if self.debug:
                logger.error(f"Request failed: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                logger.error(traceback.format_exc())
            raise Exception(f"Request failed: {e}")

class Pipe:
    class Valves(BaseModel):
        FIRECRAWL_API_KEY: str = Field(default="", description="Firecrawl API key")
        DEFAULT_FORMAT: str = Field(default="markdown", description="Default format for content extraction")
        ONLY_MAIN_CONTENT: bool = Field(default=True, description="Extract only main content")
        WAIT_FOR: int = Field(default=5000, description="Wait time in milliseconds")
        ENABLE_WEB_SEARCH: bool = Field(default=False, description="Enable web search for additional context")
        IGNORE_SITEMAP: bool = Field(default=False, description="Ignore sitemap.xml when extracting data")
        INCLUDE_SUBDOMAINS: bool = Field(default=False, description="Include subdomains when extracting data")
        SHOW_SOURCES: bool = Field(default=False, description="Show sources in the extraction results")
        BLOCK_ADS: bool = Field(default=True, description="Block ads during extraction")
        REMOVE_BASE64_IMAGES: bool = Field(default=True, description="Remove base64 encoded images from content")
        MOBILE: bool = Field(default=False, description="Use mobile user agent")
        TIMEOUT: int = Field(default=30000, description="Request timeout in milliseconds")
        LOCATION_COUNTRY: str = Field(default="US", description="Country for location-based extraction")
        LOCATION_LANGUAGES: str = Field(default="en-US", description="Comma-separated list of languages for extraction")
    
    def __init__(self):
        self.name = "Firecrawl Data Extraction Pipeline"
        
        # Private debug flag for development only
        self._debug = False
        
        # Initialize valve parameters
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        
        # Conversation state tracking
        self._conversation_state = {}
        
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

    def _normalize_url(self, url: str) -> str:
        """
        Normalize the URL by converting the protocol, domain, subdomain, and extension to lowercase.
        Everything else remains unchanged.
        """

        URL_PATTERN = re.compile(r"^(?:(https?)://)?(?:www\.)?([a-zA-Z0-9.-]+)(\.[a-zA-Z]{2,})(/.*)?$")
        match = URL_PATTERN.match(url)
        if not match:
            return url  # Return as is if it doesn't match

        protocol, domain, extension, path = match.groups()
        protocol = (protocol or "http").lower()
        domain = domain.lower()
        extension = extension.lower()
        path = path or ""

        normalized_url = f"{protocol}://{domain}{extension}{path}"

        if self._debug:
            logger.debug(f"Normalized URL: {normalized_url}")

        return normalized_url
    
    def _extract_urls_from_message(self, message: str) -> List[str]:
        """
        Extract URLs from a user message.
        """
        url_pattern = re.compile(r"https?://[^\s]+|www\.[^\s]+|(?:[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[^\s]*")
        urls = url_pattern.findall(message)

        # Initialize the Firecrawl client
        self.client = FirecrawlClient(api_key=self.valves.FIRECRAWL_API_KEY, debug=self._debug)

        if self._debug:
            logger.debug(f"Extracted URLs from message: {urls}")

        return [self._normalize_url(url) for url in urls] if urls else []
    
    def _extract_extract_id(self, message: str) -> str:
        """Extract extraction ID from user message if present"""
        id_patterns = [
            r'status of ([\w-]+)',
            r'check ([\w-]+)',
            r'extract ([\w-]+)',
            r'id ([\w-]+)',
            r'job ([\w-]+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                extract_id = match.group(1)
                if self._debug:
                    logger.debug(f"Extracted extract ID: {extract_id}")
                return extract_id
        
        if self._debug:
            logger.debug("No extract ID found in message")
        
        return None
    
    def _extract_prompt_from_message(self, message: str) -> str:
        """Extract prompt from user message"""
        # Look for prompt in quotes
        prompt_patterns = [
            r'prompt[:\s]+"(.*?)"',
            r'extract[:\s]+"(.*?)"',
            r'with prompt[:\s]+"(.*?)"',
            r'using prompt[:\s]+"(.*?)"',
        ]
        
        for pattern in prompt_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                prompt = match.group(1)
                if self._debug:
                    logger.debug(f"Extracted prompt from quotes: {prompt}")
                return prompt
        
        # If no quoted prompt found, try to extract schema-related instructions
        schema_indicators = [
            "extract", "find", "get", "retrieve", "pull", "scrape"
        ]
        
        # Check if message contains schema-related instructions
        has_schema_indicator = any(indicator in message.lower() for indicator in schema_indicators)
        
        if has_schema_indicator:
            # Remove URLs from the message to get a cleaner prompt
            urls = self._extract_urls_from_message(message)
            clean_message = message
            for url in urls:
                clean_message = clean_message.replace(url, "")
            
            # Remove common command prefixes
            prefixes = [
                "please", "can you", "could you", "i want to", "i need to", 
                "extract", "find", "get", "retrieve", "from the website"
            ]
            
            for prefix in prefixes:
                if clean_message.lower().startswith(prefix):
                    clean_message = clean_message[len(prefix):].strip()
            
            if clean_message:
                if self._debug:
                    logger.debug(f"Using message as prompt: {clean_message}")
                return clean_message
        
        # Default generic prompt if nothing specific found
        default_prompt = "Extract the main content and key information from this webpage."
        if self._debug:
            logger.debug(f"Using default prompt: {default_prompt}")
        
        return default_prompt
    
    def _extract_schema_from_message(self, message: str) -> Dict[str, Any]:
        """Extract schema from user message if present"""
        # Try to extract JSON from code blocks or plain text
        code_block_pattern = r'```(?:python|json)?\s*\n?([\s\S]*?)\n?```'
        code_blocks = re.findall(code_block_pattern, message)

        if code_blocks:
            for block in code_blocks:
                # Clean up the block by removing unnecessary spaces and line breaks
                block = block.strip()
                try:
                    schema = json.loads(block)
                    if self._debug:
                        logger.debug(f"Extracted schema from code block: {json.dumps(schema, indent=2)}")
                    return schema
                except json.JSONDecodeError:
                    if self._debug:
                        logger.error(f"Failed to parse JSON from code block: {block}")

        # Try to extract a JSON object from the message
        json_pattern = r'({[\s\S]*?})'
        matches = re.findall(json_pattern, message)

        if matches:
            for match in matches:
                # Clean up the match by removing unnecessary spaces and line breaks
                match = match.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                try:
                    schema = json.loads(match)
                    if self._debug:
                        logger.debug(f"Extracted schema from JSON: {json.dumps(schema, indent=2)}")
                    return schema
                except json.JSONDecodeError:
                    if self._debug:
                        logger.error(f"Failed to parse JSON from message: {match}")

        # No longer try to infer schema from message - require proper JSON schema
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
    
    def _format_extract_result(self, result: Dict[str, Any]) -> str:
        """Format the extraction result for display"""
        if not result or not result.get("data"):
            if result.get("status") == "processing":
                return "The extraction is still processing. Please try checking the status again in a few moments."
            else:
                return "No data was extracted."

        data = result["data"]
        
        # Build a formatted response
        response = f"### Extracted Data\n\n"
        
        # Format the extracted data
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    response += f"**{key}**:\n```json\n{json.dumps(value, indent=2)}\n```\n\n"
                else:
                    response += f"**{key}**: {value}\n\n"
        elif isinstance(data, list):
            response += "```json\n" + json.dumps(data, indent=2) + "\n```\n\n"
        else:
            response += str(data) + "\n\n"
        
        # Add status information
        if result.get("status"):
            response += f"**Status**: {result['status']}\n\n"
        
        # Add expiration information
        if result.get("expiresAt"):
            response += f"**Expires at**: {result['expiresAt']}\n\n"
        
        # Add warning if present
        if result.get("warning"):
            response += f"\n⚠️ **Warning**: {result['warning']}\n"
        
        return response

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Process the user message and perform extraction operation using Firecrawl API
        """
        logger.debug(f"pipe:{__name__}")
        
        if self._debug:
            logger.debug(f"User message: {user_message}")
            logger.debug(f"Model ID: {model_id}")
            logger.debug(f"Body: {json.dumps(body, indent=2)}")
        
        # Initialize the Firecrawl client if not already done
        if not hasattr(self, 'client'):
            self.client = FirecrawlClient(api_key=self.valves.FIRECRAWL_API_KEY, debug=self._debug)
        
        if body.get("title", False):
            return "Firecrawl Data Extraction Pipeline"
            
        # Check if this is the first message (empty or just contains a greeting)
        greeting_patterns = [
            r'^hi$', r'^hello$', r'^hey$', r'^start$', r'^begin$', r'^help$',
            r'^hi\s', r'^hello\s', r'^hey\s', r'^start\s', r'^begin\s', r'^help\s'
        ]
        
        is_greeting = not user_message or any(re.search(pattern, user_message.lower()) for pattern in greeting_patterns)
        
        if not user_message or is_greeting:
            # Reset conversation state for new conversation
            self._conversation_state = {}
            
            welcome_msg = "👋 Hello! Welcome to the Firecrawl Data Extraction Pipeline.\n\n"
            welcome_msg += "I'll help you extract structured data from websites. To get started, please tell me:\n\n"
            welcome_msg += "1. What you want to extract (e.g., 'Extract the founder's name from a website')\n"
            welcome_msg += "2. The URL(s) of the website(s)\n"
            welcome_msg += "3. The JSON schema for the data structure (must be a valid JSON object)\n\n"
            welcome_msg += "You can also check the status of a previous extraction job by typing: check status of [job-id]\n\n"
            welcome_msg += "Let's begin! What would you like to extract?"
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
        
        # Check if user wants to restart the conversation
        if any(keyword in user_message.lower() for keyword in ["restart", "start over", "reset", "begin again"]):
            self._conversation_state = {}
            return "Let's start over. What would you like to extract?"
        
        # Check if user is requesting extraction status
        extract_id = self._extract_extract_id(user_message)
        if extract_id and ("status" in user_message.lower() or "check" in user_message.lower()):
            try:
                if self._debug:
                    logger.debug(f"Checking status for extract ID: {extract_id}")
                
                request = ExtractStatusRequest(id=extract_id)
                response = self.client.get_extract_status(request)
                
                if self._debug:
                    logger.debug(f"Extract status response: {response.model_dump()}")
                
                # Check if there was an error
                if response.error:
                    return f"Error getting extraction status: {response.error}"
                
                # Format and return the extraction result
                return self._format_extract_result(response.model_dump())
            except Exception as e:
                error_msg = f"Error getting extraction status: {str(e)}"
                logger.error(error_msg)
                
                if self._debug:
                    logger.error(traceback.format_exc())
                    return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
                
                return error_msg
        
        # Handle the conversational flow for extraction
        # Step 1: Get the prompt (what to extract)
        if "prompt" not in self._conversation_state:
            # Try to extract prompt from the message
            prompt = self._extract_prompt_from_message(user_message)
            
            # If we found a prompt, store it and move to the next step
            if prompt and prompt != "Extract the main content and key information from this webpage.":
                self._conversation_state["prompt"] = prompt
                
                # Check if URLs are also provided in the same message
                urls = self._extract_urls_from_message(user_message)
                if urls:
                    self._conversation_state["urls"] = urls
                    
                    # Check if schema is also provided in the same message
                    schema = self._extract_schema_from_message(user_message)
                    if schema:
                        self._conversation_state["schema"] = schema
                        
                        # We have all the information, proceed with extraction
                        confirmation = f"Great! I'll extract the following data:\n\n"
                        confirmation += f"- Prompt: {prompt}\n"
                        confirmation += f"- URLs: {', '.join(urls)}\n"
                        confirmation += f"- Schema: {json.dumps(schema, indent=2)}\n\n"
                        confirmation += "Processing your request now..."
                        
                        # Proceed with extraction
                        try:
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
                            
                            # Add location if specified
                            location = self._parse_location(self.valves.LOCATION_COUNTRY, self.valves.LOCATION_LANGUAGES)
                            if location:
                                scrape_options["location"] = location
                            
                            # Create request with all parameters
                            request_data = {
                                "urls": urls,
                                "prompt": prompt,
                                "schema": schema,
                                "enableWebSearch": self.valves.ENABLE_WEB_SEARCH,
                                "ignoreSitemap": self.valves.IGNORE_SITEMAP,
                                "includeSubdomains": self.valves.INCLUDE_SUBDOMAINS,
                                "showSources": self.valves.SHOW_SOURCES,
                                "scrapeOptions": scrape_options
                            }
                            
                            # For debugging, show the exact request that will be sent
                            if self._debug:
                                logger.debug(f"Raw request data: {json.dumps(request_data, indent=2)}")
                            
                            request = ExtractRequest(**request_data)
                            
                            if self._debug:
                                logger.debug(f"Created extract request: {request.model_dump()}")
                            
                            response = self.client.extract_data(request)
                            
                            if self._debug:
                                logger.debug(f"Received extract response: {response.model_dump()}")
                            
                            # Reset conversation state after successful extraction
                            self._conversation_state = {}
                            
                            # Return success message with extraction ID
                            return (f"{confirmation}\n\nExtraction job started with ID: {response.id}. Status: {'successful' if response.success else 'failed'}\n\n"
                                   f"To check the status and results later, ask: 'Check status of {response.id}'")
                        except Exception as e:
                            error_msg = f"Error during extraction operation: {str(e)}"
                            logger.error(error_msg)
                            
                            if self._debug:
                                logger.error(traceback.format_exc())
                                return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
                            
                            return error_msg
                    
                    # If we have prompt and URLs but no schema, ask for schema
                    complex_example = {
                        "type": "object",
                        "properties": {
                            "founders": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "name"
                                    ]
                                }
                            }
                        },
                        "required": [
                            "founders"
                        ]
                    }
                    
                    return f"Great! I'll extract: '{prompt}'\n\nNow, please provide ONLY the JSON schema for the data in your next message.\n\nHere's an example schema that would extract an array of founders with their names:\n\n```json\n{json.dumps(complex_example, indent=2)}\n```"
                else:
                    return f"Great! I'll extract: '{prompt}'\n\nNow, please provide the URL(s) of the website(s) you want to extract data from."
            else:
                # If no clear prompt was found, ask explicitly
                return "Please tell me what you want to extract from the website. For example: 'Extract the founder's name' or 'Find product prices and descriptions'."
        
        # Step 2: Get the URLs if not already provided
        if "prompt" in self._conversation_state and "urls" not in self._conversation_state:
            urls = self._extract_urls_from_message(user_message)
            if urls:
                self._conversation_state["urls"] = urls
                
                # Provide complex schema example
                complex_example = {
                    "type": "object",
                    "properties": {
                        "founders": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "name"
                                ]
                            }
                        }
                    },
                    "required": [
                        "founders"
                    ]
                }
                
                return f"Thanks for the URL(s). Now, please provide ONLY the JSON schema for the data in your next message.\n\nHere's an example schema that would extract an array of founders with their names:\n\n```json\n{json.dumps(complex_example, indent=2)}\n```"
            else:
                return "I need the URL(s) of the website(s) you want to extract data from. Please provide at least one valid URL."
        
        # Step 3: Get the schema
        if "prompt" in self._conversation_state and "urls" in self._conversation_state and "schema" not in self._conversation_state:
            schema = self._extract_schema_from_message(user_message)
            
            # If no schema was found or it's empty, ask explicitly
            if not schema:
                schema_example = {
                    "type": "object",
                    "properties": {
                        "founders": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "name"
                                ]
                            }
                        }
                    },
                    "required": [
                        "founders"
                    ]
                }
                
                return f"I need a valid JSON schema to structure the extracted data. Please provide ONLY the schema JSON in your next message.\n\nHere's an example schema that would extract an array of founders with their names:\n\n```json\n{json.dumps(schema_example, indent=2)}\n```\n\nPlease refer to the documentation or the example above for the proper schema format."
            
            self._conversation_state["schema"] = schema
            
            # Now we have all required information, confirm and proceed
            prompt = self._conversation_state["prompt"]
            urls = self._conversation_state["urls"]
            
            confirmation = f"Great! I'll extract the following data:\n\n"
            confirmation += f"- Prompt: {prompt}\n"
            confirmation += f"- URLs: {', '.join(urls)}\n"
            confirmation += f"- Schema: {json.dumps(schema, indent=2)}\n\n"
            confirmation += "Processing your request now..."
            
            # Proceed with extraction
            try:
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
                
                # Add location if specified
                location = self._parse_location(self.valves.LOCATION_COUNTRY, self.valves.LOCATION_LANGUAGES)
                if location:
                    scrape_options["location"] = location
                
                # Create request with all parameters
                request_data = {
                    "urls": urls,
                    "prompt": prompt,
                    "schema": schema,
                    "enableWebSearch": self.valves.ENABLE_WEB_SEARCH,
                    "ignoreSitemap": self.valves.IGNORE_SITEMAP,
                    "includeSubdomains": self.valves.INCLUDE_SUBDOMAINS,
                    "showSources": self.valves.SHOW_SOURCES,
                    "scrapeOptions": scrape_options
                }
                
                # For debugging, show the exact request that will be sent
                if self._debug:
                    logger.debug(f"Raw request data: {json.dumps(request_data, indent=2)}")
                
                request = ExtractRequest(**request_data)
                
                if self._debug:
                    logger.debug(f"Created extract request: {request.model_dump()}")
                
                response = self.client.extract_data(request)
                
                if self._debug:
                    logger.debug(f"Received extract response: {response.model_dump()}")
                
                # Reset conversation state after successful extraction
                self._conversation_state = {}
                
                # Return success message with extraction ID
                return (f"{confirmation}\n\nExtraction job started with ID: {response.id}. Status: {'successful' if response.success else 'failed'}\n\n"
                       f"To check the status and results later, ask: 'Check status of {response.id}'")
            except Exception as e:
                error_msg = f"Error during extraction operation: {str(e)}"
                logger.error(error_msg)
                
                if self._debug:
                    logger.error(traceback.format_exc())
                    return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
                
                return error_msg
        
        # If we already have all the information, check if the user is providing new information
        if "prompt" in self._conversation_state and "urls" in self._conversation_state and "schema" in self._conversation_state:
            # Check if user is providing new URLs
            urls = self._extract_urls_from_message(user_message)
            if urls:
                self._conversation_state["urls"] = urls
                return f"I've updated the URLs to: {', '.join(urls)}. Do you want to proceed with the extraction using the current prompt and schema?"
            
            # Check if user is providing a new schema
            schema = self._extract_schema_from_message(user_message)
            if schema:
                self._conversation_state["schema"] = schema
                return f"I've updated the schema to: {json.dumps(schema, indent=2)}. Do you want to proceed with the extraction using the current prompt and URLs?"
            
            # Check if user is providing a new prompt
            prompt = self._extract_prompt_from_message(user_message)
            if prompt and prompt != "Extract the main content and key information from this webpage.":
                self._conversation_state["prompt"] = prompt
                return f"I've updated the prompt to: '{prompt}'. Do you want to proceed with the extraction using the current URLs and schema?"
            
            # If user confirms or says yes, proceed with extraction
            if any(keyword in user_message.lower() for keyword in ["yes", "proceed", "continue", "go ahead", "extract", "start"]):
                prompt = self._conversation_state["prompt"]
                urls = self._conversation_state["urls"]
                schema = self._conversation_state["schema"]
                
                confirmation = f"Great! I'll extract the following data:\n\n"
                confirmation += f"- Prompt: {prompt}\n"
                confirmation += f"- URLs: {', '.join(urls)}\n"
                confirmation += f"- Schema: {json.dumps(schema, indent=2)}\n\n"
                confirmation += "Processing your request now..."
                
                # Proceed with extraction
                try:
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
                    
                    # Add location if specified
                    location = self._parse_location(self.valves.LOCATION_COUNTRY, self.valves.LOCATION_LANGUAGES)
                    if location:
                        scrape_options["location"] = location
                    
                    # Create request with all parameters
                    request_data = {
                        "urls": urls,
                        "prompt": prompt,
                        "schema": schema,
                        "enableWebSearch": self.valves.ENABLE_WEB_SEARCH,
                        "ignoreSitemap": self.valves.IGNORE_SITEMAP,
                        "includeSubdomains": self.valves.INCLUDE_SUBDOMAINS,
                        "showSources": self.valves.SHOW_SOURCES,
                        "scrapeOptions": scrape_options
                    }
                    
                    # For debugging, show the exact request that will be sent
                    if self._debug:
                        logger.debug(f"Raw request data: {json.dumps(request_data, indent=2)}")
                    
                    request = ExtractRequest(**request_data)
                    
                    if self._debug:
                        logger.debug(f"Created extract request: {request.model_dump()}")
                    
                    response = self.client.extract_data(request)
                    
                    if self._debug:
                        logger.debug(f"Received extract response: {response.model_dump()}")
                    
                    # Reset conversation state after successful extraction
                    self._conversation_state = {}
                    
                    # Return success message with extraction ID
                    return (f"{confirmation}\n\nExtraction job started with ID: {response.id}. Status: {'successful' if response.success else 'failed'}\n\n"
                           f"To check the status and results later, ask: 'Check status of {response.id}'")
                except Exception as e:
                    error_msg = f"Error during extraction operation: {str(e)}"
                    logger.error(error_msg)
                    
                    if self._debug:
                        logger.error(traceback.format_exc())
                        return f"{error_msg}\n\nDebug traceback:\n{traceback.format_exc()}"
                    
                    return error_msg
            
            # If user says no, ask what they want to change
            if any(keyword in user_message.lower() for keyword in ["no", "change", "modify", "update", "edit"]):
                return "What would you like to change? You can update the prompt, URLs, or schema."
            
            # Default response if we can't determine what the user wants
            return "I have all the information needed for extraction. Please say 'yes' to proceed, 'no' to make changes, or 'restart' to start over."
        
        # If we reach here, something unexpected happened
        return "I'm not sure what you want to do. Please say 'restart' to start over, or provide the information I'm asking for."

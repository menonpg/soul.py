"""
SoulMate API Client

A Python client for the SoulMate hosted memory service.
"""

import requests
from typing import Optional, Dict, Any, List


class SoulMateClient:
    """
    Client for SoulMate — Persistent AI Memory as a Service.
    
    SoulMate provides hosted memory infrastructure for AI agents.
    BYOK (Bring Your Own Key) model — you provide your LLM API key,
    SoulMate handles persistent per-customer memory.
    
    Example:
        >>> from soulmate import SoulMateClient
        >>> sm = SoulMateClient(
        ...     api_key="sm_live_xxxxx",
        ...     llm_provider="anthropic",
        ...     llm_key="sk-ant-api03-..."
        ... )
        >>> response = sm.ask("customer_123", "What's my order history?")
        >>> print(response)
    """
    
    DEFAULT_BASE_URL = "https://soulmate-api-production.up.railway.app"
    
    def __init__(
        self,
        api_key: str,
        llm_provider: str = "anthropic",
        llm_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize the SoulMate client.
        
        Args:
            api_key: Your SoulMate API key (starts with sm_live_ or sm_test_)
            llm_provider: LLM provider to use ("anthropic", "openai", or "ollama")
            llm_key: Your LLM provider API key (required for anthropic/openai)
            base_url: Override the default SoulMate API URL (for self-hosted)
            timeout: Request timeout in seconds (default: 60)
        """
        self.api_key = api_key
        self.llm_provider = llm_provider
        self.llm_key = llm_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        
        response = self._session.request(
            method=method,
            url=url,
            json=json,
            params=params,
            timeout=self.timeout,
        )
        
        if response.status_code >= 400:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                pass
            raise SoulMateError(
                f"API error ({response.status_code}): {error_msg}",
                status_code=response.status_code,
            )
        
        return response.json()
    
    def ask(
        self,
        customer_id: str,
        message: str,
        soul_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a message and get a response with persistent memory.
        
        The conversation history and context for this customer_id is
        automatically maintained across calls.
        
        Args:
            customer_id: Unique identifier for the customer/user
            message: The user's message
            soul_id: Optional soul configuration to use (default: "default")
            system_prompt: Optional system prompt override
            
        Returns:
            The assistant's response text
        """
        payload = {
            "customer_id": customer_id,
            "message": message,
            "llm_provider": self.llm_provider,
            "llm_key": self.llm_key,
        }
        
        if soul_id:
            payload["soul_id"] = soul_id
        if system_prompt:
            payload["system_prompt"] = system_prompt
        
        result = self._request("POST", "/v1/ask", json=payload)
        return result.get("response", "")
    
    def get_memory(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieve the stored memory for a customer.
        
        Args:
            customer_id: Unique identifier for the customer/user
            
        Returns:
            Dictionary containing the customer's memory data
        """
        return self._request("GET", f"/v1/memory/{customer_id}")
    
    def delete_memory(self, customer_id: str) -> Dict[str, Any]:
        """
        Delete all stored memory for a customer (GDPR compliance).
        
        Args:
            customer_id: Unique identifier for the customer/user
            
        Returns:
            Confirmation of deletion
        """
        return self._request("DELETE", f"/v1/memory/{customer_id}")
    
    def upload_soul(
        self,
        soul_id: str,
        content: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a SOUL.md configuration.
        
        Args:
            soul_id: Unique identifier for this soul configuration
            content: The SOUL.md content (markdown)
            description: Optional description
            
        Returns:
            Confirmation with soul details
        """
        payload = {
            "soul_id": soul_id,
            "content": content,
        }
        if description:
            payload["description"] = description
        
        return self._request("POST", "/v1/souls", json=payload)
    
    def list_souls(self) -> List[Dict[str, Any]]:
        """
        List all uploaded soul configurations.
        
        Returns:
            List of soul configurations
        """
        result = self._request("GET", "/v1/souls")
        return result.get("souls", [])
    
    def get_usage(self) -> Dict[str, Any]:
        """
        Get usage statistics for your API key.
        
        Returns:
            Usage data including request counts, memory operations, etc.
        """
        return self._request("GET", "/v1/usage")
    
    @classmethod
    def signup(
        cls,
        email: str,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sign up for a new SoulMate API key.
        
        Args:
            email: Your email address
            base_url: Override the default SoulMate API URL
            
        Returns:
            Dictionary containing your new API key
        """
        url = (base_url or cls.DEFAULT_BASE_URL).rstrip("/")
        response = requests.post(
            f"{url}/v1/signup",
            json={"email": email},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


class SoulMateError(Exception):
    """Exception raised for SoulMate API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

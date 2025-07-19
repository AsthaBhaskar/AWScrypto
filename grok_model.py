import requests
import json
from typing import Dict, Any, Optional, List, Iterator

class GrokModel:
    """
    A model wrapper for xAI Grok API that mimics the OpenAIModel interface.
    """
    
    def __init__(self, client_args: Dict[str, Any], model_id: str = "grok-3", params: Optional[Dict[str, Any]] = None):
        """
        Initialize the Grok model.
        
        Args:
            client_args: Dictionary containing API key and other client arguments
            model_id: The Grok model to use (grok-4 or grok-3)
            params: Additional parameters for the API call
        """
        self.api_key = client_args.get("api_key")
        if not self.api_key:
            raise ValueError("API key is required in client_args")
        
        self.model_id = model_id
        self.params = params or {}
        self.base_url = "https://api.x.ai/v1"
        
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request to xAI Grok API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters to override default params
            
        Returns:
            Dictionary containing the API response
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Merge default params with kwargs
        request_params = {**self.params, **kwargs}
        
        # Fix: Flatten message content to string if needed
        fixed_messages = []
        for msg in messages:
            new_msg = dict(msg)
            content = new_msg.get("content")
            if isinstance(content, list):
                # If content is a list of dicts with 'text', join them
                if all(isinstance(x, dict) and "text" in x for x in content):
                    new_msg["content"] = " ".join(x["text"] for x in content)
                else:
                    new_msg["content"] = " ".join(str(x) for x in content)
            elif isinstance(content, dict) and "text" in content:
                new_msg["content"] = content["text"]
            # else: leave as is (should be string)
            fixed_messages.append(new_msg)

        payload = {
            "model": self.model_id,
            "messages": fixed_messages,
            **request_params
        }
        
        try:
            print("[GROK DEBUG] Payload:")
            print(json.dumps(payload, indent=2))
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("[GROK DEBUG] Response content:")
                print(response.text)
                raise
            return response.json()
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Grok API request timed out: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Grok API: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Grok API request failed: {str(e)}")
    
    async def stream(self, *args, **kwargs):
        """
        Async stream chat completion responses (non-streaming implementation).
        Accepts arbitrary arguments for compatibility with strands library.
        """
        messages = None
        if args:
            messages = args[0]
        if messages is None:
            messages = kwargs.get('messages')
        if messages is None:
            raise ValueError("No messages provided to GrokModel.stream")
        response = self.chat_completion(messages, **kwargs)
        yield response
    
    def __call__(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Convenience method to call chat_completion.
        """
        return self.chat_completion(messages, **kwargs) 
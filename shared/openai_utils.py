"""
OpenAI utilities for AI-powered features across projects
"""

import os
import logging
from typing import List, Dict, Optional, Any
import openai
from openai import OpenAI
import tiktoken
from functools import wraps
import time

# Set up logging
logger = logging.getLogger(__name__)

class OpenAIManager:
    """
    Centralized OpenAI API management for all portfolio projects
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client
        
        Args:
            api_key (str, optional): OpenAI API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.default_model = "gpt-4"
        self.max_retries = 3
        self.retry_delay = 1
    
    def retry_on_failure(func):
        """Decorator for retrying API calls on failure"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"API call failed after {self.max_retries} attempts: {e}")
                        raise
                    logger.warning(f"API call failed (attempt {attempt + 1}), retrying: {e}")
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
            return None
        return wrapper
    
    @retry_on_failure
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate chat completion using OpenAI API
        
        Args:
            messages (List[Dict]): Conversation messages
            model (str, optional): Model to use (defaults to gpt-4)
            temperature (float): Sampling temperature
            max_tokens (int, optional): Maximum tokens to generate
            **kwargs: Additional parameters for the API call
            
        Returns:
            str: Generated response
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise
    
    @retry_on_failure
    def analyze_image(
        self,
        image_url: str,
        prompt: str,
        model: str = "gpt-4-vision-preview",
        max_tokens: int = 500
    ) -> str:
        """
        Analyze image using OpenAI Vision API
        
        Args:
            image_url (str): URL or base64 encoded image
            prompt (str): Analysis prompt
            model (str): Vision model to use
            max_tokens (int): Maximum response tokens
            
        Returns:
            str: Analysis result
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise
    
    @retry_on_failure
    def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002"
    ) -> List[List[float]]:
        """
        Generate embeddings for text inputs
        
        Args:
            texts (List[str]): List of texts to embed
            model (str): Embedding model to use
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens in text for a specific model
        
        Args:
            text (str): Text to count tokens for
            model (str): Model to use for token counting
            
        Returns:
            int: Number of tokens
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed, using approximation: {e}")
            return len(text.split()) * 1.3  # Rough approximation
    
    def create_system_message(self, system_prompt: str) -> Dict[str, str]:
        """
        Create a system message for chat completion
        
        Args:
            system_prompt (str): System prompt content
            
        Returns:
            Dict[str, str]: Formatted system message
        """
        return {"role": "system", "content": system_prompt}
    
    def create_user_message(self, user_input: str) -> Dict[str, str]:
        """
        Create a user message for chat completion
        
        Args:
            user_input (str): User input content
            
        Returns:
            Dict[str, str]: Formatted user message
        """
        return {"role": "user", "content": user_input}
    
    def create_assistant_message(self, assistant_response: str) -> Dict[str, str]:
        """
        Create an assistant message for chat completion
        
        Args:
            assistant_response (str): Assistant response content
            
        Returns:
            Dict[str, str]: Formatted assistant message
        """
        return {"role": "assistant", "content": assistant_response}

# Project-specific prompt templates
class PromptTemplates:
    """
    Centralized prompt templates for different projects
    """
    
    # StockSense prompts
    STOCKSENSE_SYSTEM = """
    You are an AI assistant specializing in inventory management and supply chain optimization.
    You help analyze stockout risks and provide actionable recommendations for inventory managers.
    Always be specific, data-driven, and focus on business impact.
    """
    
    # Smart Cart prompts
    SMART_CART_SYSTEM = """
    You are a helpful shopping assistant AI. You help customers find products, make recommendations,
    and optimize their shopping experience. Be friendly, knowledgeable, and always aim to provide
    value to the customer while being honest about product limitations.
    """
    
    # Compliance Scout prompts
    COMPLIANCE_SCOUT_SYSTEM = """
    You are an accessibility expert AI that analyzes websites for WCAG compliance.
    Identify accessibility issues, provide specific remediation recommendations,
    and explain the impact on users with disabilities. Be thorough and constructive.
    """
    
    @staticmethod
    def format_product_recommendation(products: List[Dict], user_context: str) -> str:
        """Format product recommendation prompt"""
        product_list = "\n".join([
            f"- {p['name']}: ${p['price']} - {p['description']}"
            for p in products
        ])
        
        return f"""
        User Context: {user_context}
        
        Available Products:
        {product_list}
        
        Provide personalized recommendations explaining why each product matches the user's needs.
        """
    
    @staticmethod
    def format_accessibility_analysis(html_content: str, violations: List[Dict]) -> str:
        """Format accessibility analysis prompt"""
        violation_list = "\n".join([
            f"- {v['type']}: {v['description']} (Impact: {v['impact']})"
            for v in violations
        ])
        
        return f"""
        HTML Content Analysis:
        {html_content[:1000]}...
        
        Detected Violations:
        {violation_list}
        
        Provide a comprehensive accessibility analysis with specific remediation steps.
        """

# Utility functions
def setup_openai_logging(level: int = logging.INFO):
    """
    Set up logging for OpenAI utilities
    
    Args:
        level (int): Logging level
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_api_key(api_key: str) -> bool:
    """
    Validate OpenAI API key format
    
    Args:
        api_key (str): API key to validate
        
    Returns:
        bool: True if format is valid
    """
    return api_key and api_key.startswith("sk-") and len(api_key) > 20

# Example usage and testing
def main():
    """
    Example usage of OpenAI utilities
    """
    try:
        # Initialize manager
        openai_manager = OpenAIManager()
        
        # Test basic chat completion
        messages = [
            openai_manager.create_system_message(PromptTemplates.SMART_CART_SYSTEM),
            openai_manager.create_user_message("I'm looking for a warm winter coat under $100")
        ]
        
        response = openai_manager.chat_completion(messages, temperature=0.7)
        print("Chat Response:", response)
        
        # Test token counting
        token_count = openai_manager.count_tokens("Hello, how are you today?")
        print(f"Token count: {token_count}")
        
        logger.info("OpenAI utilities test completed successfully")
        
    except Exception as e:
        logger.error(f"OpenAI utilities test failed: {e}")

if __name__ == "__main__":
    setup_openai_logging()
    main()
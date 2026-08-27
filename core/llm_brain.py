"""
LLM client for strategic decisions using NVIDIA API (OpenAI-compatible).
Fallback to rule-based if API fails.
"""
import os
import json
import time
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class LLMBrain:
    def __init__(self):
        self.api_key = os.getenv('LLM_API_KEY')
        self.base_url = os.getenv('LLM_API_URL', 'https://integrate.api.nvidia.com/v1')
        self.model = os.getenv('LLM_MODEL', 'meta/llama-3.1-70b-instruct')
        self.timeout = 30
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def query(self, prompt):
        """Send prompt to NVIDIA LLM and return raw response."""
        if not self.client:
            logger.warning("No LLM API key set. Falling back to offline rules.")
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.7,
            )
            # Return full response object (or just content)
            return response
        except Exception as e:
            logger.error("LLM API call failed: %s", e)
            return None

    def parse_actions(self, response):
        """Extract JSON list of actions from LLM response."""
        if not response:
            return None
        try:
            # For OpenAI-compatible response
            text = response.choices[0].message.content
            # Find JSON block (may be wrapped in ```json)
            if '```json' in text:
                json_str = text.split('```json')[1].split('```')[0].strip()
            else:
                json_str = text.strip()
            actions = json.loads(json_str)
            if isinstance(actions, list):
                return actions
        except Exception as e:
            logger.error("Failed to parse LLM response: %s", e)
            return None
        return None
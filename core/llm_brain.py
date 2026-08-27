"""
LLM client for strategic decisions. Fallback to rule-based if API fails.
"""
import os
import json
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMBrain:
    def __init__(self):
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_url = os.getenv('LLM_API_URL', 'https://api.anthropic.com/v1/messages')
        self.model = os.getenv('LLM_MODEL', 'claude-3-haiku-20240307')
        self.timeout = 30

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def query(self, prompt):
        if not self.api_key:
            return None
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        payload = {
            'model': self.model,
            'max_tokens': 1024,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        try:
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            # Fallback: return None to trigger rule-based
            return None

    def parse_actions(self, response):
        """Extract JSON list of actions from LLM response."""
        if not response:
            return None
        try:
            # Anthropic response structure: content[0].text
            text = response['content'][0]['text']
            # Find JSON block (may be wrapped in ```json)
            if '```json' in text:
                json_str = text.split('```json')[1].split('```')[0].strip()
            else:
                json_str = text.strip()
            actions = json.loads(json_str)
            if isinstance(actions, list):
                return actions
        except Exception:
            return None
        return None

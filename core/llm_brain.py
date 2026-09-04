"""
LLM client for strategic decisions using NVIDIA API (OpenAI-compatible).
"""
import os
import json
import re
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
        self.timeout = 120
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def query(self, prompt):
        if not self.client:
            logger.warning("No LLM API key set. Falling back to offline rules.")
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security automation assistant. Respond ONLY with a JSON array of actions. Do not include any explanations, markdown, or extra text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.7,
            )
            return response
        except Exception as e:
            logger.error("LLM API call failed: %s", e)
            return None

    def parse_actions(self, response):
        if not response:
            return None
        try:
            text = response.choices[0].message.content
            logger.info("LLM raw response (first 500 chars): %s", text[:500])

            if not text or not text.strip():
                logger.warning("LLM response is empty.")
                return None

            # -----------------------------------------------------------------
            # Helper: find the last balanced JSON array or object in text
            # -----------------------------------------------------------------
            def find_last_json(txt):
                # Try to find the last occurrence of '[' or '{' that is properly closed
                for start_char, end_char in [('[', ']'), ('{', '}')]:
                    start = txt.rfind(start_char)
                    if start == -1:
                        continue
                    depth = 0
                    for i in range(start, len(txt)):
                        if txt[i] == start_char:
                            depth += 1
                        elif txt[i] == end_char:
                            depth -= 1
                            if depth == 0:
                                candidate = txt[start:i+1]
                                try:
                                    json.loads(candidate)
                                    return candidate
                                except:
                                    # Try to parse from start to end
                                    pass
                    # If we didn't find a balanced structure, try the whole substring
                    try:
                        candidate = txt[start:]
                        json.loads(candidate)
                        return candidate
                    except:
                        pass
                return None

            json_str = find_last_json(text)

            if not json_str:
                # Fallback: extract all JSON objects and combine
                def extract_all_objects(txt):
                    objects = []
                    i = 0
                    while i < len(txt):
                        while i < len(txt) and txt[i] not in '{[':
                            i += 1
                        if i >= len(txt):
                            break
                        start = i
                        stack = []
                        while i < len(txt):
                            ch = txt[i]
                            if ch in '{[':
                                stack.append(ch)
                            elif ch in '}]':
                                if stack:
                                    top = stack.pop()
                                    if (ch == '}' and top != '{') or (ch == ']' and top != '['):
                                        i += 1
                                        break
                                    if not stack:
                                        end = i + 1
                                        try:
                                            obj = json.loads(txt[start:end])
                                            objects.append(obj)
                                        except:
                                            pass
                                        i = end
                                        break
                            i += 1
                        if stack:
                            # Unbalanced, skip
                            i = start + 1
                    return objects

                objects = extract_all_objects(text)
                if not objects:
                    logger.warning("No JSON objects found in LLM response.")
                    return None
                # Flatten
                actions = []
                for obj in objects:
                    if isinstance(obj, list):
                        actions.extend(obj)
                    elif isinstance(obj, dict):
                        if 'actions' in obj:
                            actions.extend(obj['actions'])
                        else:
                            actions.append(obj)
                return actions if actions else None

            # -----------------------------------------------------------------
            # Parse the extracted JSON
            # -----------------------------------------------------------------
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if 'actions' in data:
                    return data['actions']
                return [data]
            else:
                return None

        except Exception as e:
            logger.error("Failed to parse LLM response: %s", e)
            return None

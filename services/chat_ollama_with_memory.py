import redis
from langchain_ollama import ChatOllama
from enum import Enum
from typing import Dict, Any, Optional
from enums.redis_operation import RedisOperation
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# System prompt with Redis instructions
SYSTEM_PROMPT = """
You are a helpful assistant with the ability to store and retrieve information using Redis, a fast in-memory database. You can use Redis to remember important details about the user or context that might be helpful for future interactions.

### How to Interact with Redis:
1. **Store Data**:
   - Use the `STORE` operation to save information in Redis.
   - Output format: `{"operation": "STORE", "key": "<key>", "value": "<value>"}`
   - Example: To remember that the user prefers poetry, output: `{"operation": "STORE", "key": "user:123:preference", "value": "prefers poetry"}`

2. **Retrieve Data**:
   - Use the `RETRIEVE` operation to fetch information from Redis.
   - Output format: `{"operation": "RETRIEVE", "key": "<key>"}`
   - Example: To retrieve the user's preference, output: `{"operation": "RETRIEVE", "key": "user:123:preference"}`

3. **Delete Data**:
   - Use the `DELETE` operation to remove information from Redis.
   - Output format: `{"operation": "DELETE", "key": "<key>"}`
   - Example: To delete the user's preference, output: `{"operation": "DELETE", "key": "user:123:preference"}`

### Important Notes:
- Always output valid JSON when interacting with Redis.
- After performing a Redis operation, wait for the result before generating a final response.
- Use Redis to remember user preferences, conversation history, or any other relevant information.
"""

# Wrapper class for ChatOllama with Redis integration
class ChatOllamaWithMemory:
    def __init__(self, model: str, redis_host: str = "localhost", redis_port: int = 6379):
        self.chat = ChatOllama(model=model)
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

    def _extract_thinking_and_output(self, content: str) -> tuple[str, str]:
        """
        Extract the thinking process and final output from the model's response.
        """
        thinking_start = content.find("<think>")
        thinking_end = content.find("</think>")

        if thinking_start != -1 and thinking_end != -1:
            thinking_process = content[thinking_start + len("<think>") : thinking_end].strip()
            final_output = content[thinking_end + len("</think>") :].strip()
            return thinking_process, final_output
        else:
            return "", content

    def _parse_model_output(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Parse the model's output to check for Redis operations.
        Example output: {"operation": "STORE", "key": "user:123", "value": "prefers poetry"}
        """
        try:
            import json
            return json.loads(output)
        except json.JSONDecodeError:
            return None

    def _handle_redis_operation(self, operation: Dict[str, Any]) -> Optional[str]:
        """
        Handle Redis operations based on the model's output.
        """
        op = operation.get("operation")
        key = operation.get("key")
        value = operation.get("value")

        if op == RedisOperation.STORE:
            if key and value:
                self.redis.set(key, value)
                return f"Stored {value} under {key}"
        elif op == RedisOperation.RETRIEVE:
            if key:
                return self.redis.get(key)
        elif op == RedisOperation.DELETE:
            if key:
                self.redis.delete(key)
                return f"Deleted {key}"
        return None

    def invoke(self, message: list) -> str:
        """
        Intercept the model's output, handle Redis operations, and return the final response.
        """
        # Add the system prompt to the message
        message_with_prompt = [("system", SYSTEM_PROMPT)] + message

        # Get the model's response
        ai_response = self.chat.invoke(message_with_prompt)
        content = ai_response.content

        # Extract thinking process and final output
        thinking_process, final_output = self._extract_thinking_and_output(content)

        # Log the thinking process
        if thinking_process:
            logger.info(f"Thinking Process: {thinking_process}")

        # Check if the final output contains Redis operations
        parsed_output = self._parse_model_output(final_output)
        if parsed_output and "operation" in parsed_output:
            redis_result = self._handle_redis_operation(parsed_output)
            if redis_result:
                # Pass the Redis result back to the model for further processing
                follow_up_message = message_with_prompt + [("system", f"Redis operation succeded, results: {redis_result}")]
                follow_up_response = self.chat.invoke(follow_up_message)
                # Extract thinking process and final output
                thinking_process, final_output = self._extract_thinking_and_output(follow_up_response.content)

                # Log the thinking process
                if thinking_process:
                    logger.info(f"Thinking Process: {thinking_process}")
                return final_output

        # If no Redis operation, return the final output
        return final_output
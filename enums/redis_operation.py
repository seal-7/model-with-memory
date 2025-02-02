from enum import Enum

class RedisOperation(str, Enum):
    STORE = "STORE"  # Store data in Redis
    RETRIEVE = "RETRIEVE"  # Retrieve data from Redis
    DELETE = "DELETE"  # Delete data from Redis
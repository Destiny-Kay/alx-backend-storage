#!/usr/bin/env python3
"""0. Writing strings to Redis
1. Reading from Redis and recovering
original type
"""
import redis
import uuid
import functools
from typing import Union, Callable, Optional


def replay(method: Callable) -> None:
    """Display the history of calls of a particular function.
    Args:
        method (Callable): The function to display the history for.
    """
    r = method.__self__._redis
    qualname = method.__qualname__
    inputs_key = f"{qualname}:inputs"
    outputs_key = f"{qualname}:outputs"

    num_calls = r.get(qualname)
    if num_calls:
        num_calls = num_calls.decode('utf-8')
    else:
        num_calls = '0'

    inputs = r.lrange(inputs_key, 0, -1)
    outputs = r.lrange(outputs_key, 0, -1)

    print(f"{qualname} was called {num_calls} times:")

    for input_, output in zip(inputs, outputs):
        input_ = input_.decode('utf-8')
        output = output.decode('utf-8')
        print(f"{qualname}(*{input_}) -> {output}")


def count_calls(method: Callable) -> Callable:
    """
        Wrapper that counts the number of times the cache methods are called
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        """Wrapper func
        """
        key = method.__qualname__
        self._redis.incr(key)
        return method(self, *args, **kwargs)
    return wrapper


def call_history(method: Callable) -> Callable:
    """
    Stores history of inputs and outputs of a particular function
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        """Wrapper
        """
        input_key = method.__qualname__ + ":inputs"
        output_key = method.__qualname__ + ":outputs"

        self._redis.rpush(input_key, str(args))
        result = method(self, *args, **kwargs)
        self._redis.rpush(output_key, str(result))

        return result
    return wrapper


class Cache:
    """Cache class
    """
    def __init__(self) -> None:
        """ A redis class initialization
        """
        self._redis = redis.Redis()
        self._redis.flushdb()

    @count_calls
    @call_history
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """Generates a random uuid key and returns it
        """
        key = str(uuid.uuid4())
        if isinstance(data, (int, float)):
            data = str(data)
        self._redis.set(name=key, value=data)
        return key

    def get(self, key: str, fn: Optional[Callable] =
            None) -> Union[str, bytes, int, float]:
        """
        Redis get.
        Args:
            key: String argument
            fn: converts data back to desired format
        """
        value = self._redis.get(name=key)
        if value is None:
            return value
        if fn:
            return fn(value)
        return value

    def get_str(self, key: str) -> Optional[str]:
        """
            Parametrizes cache.get with correct conversion function
        """
        return self.get(key, fn=lambda x: x.decode('utf-8'))

    def get_int(self, key: str) -> Optional[int]:
        """
            Parametrizes cache.get with correct conversion function
        """
        value = self.get(key)
        return int(value) if value else None

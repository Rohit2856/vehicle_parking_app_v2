import redis
import json
import hashlib
from functools import wraps
from flask import request, make_response

class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 300  

    def generate_cache_key(self, prefix, **kwargs):  # generate unique cache key with query parameters
        key_parts = [prefix]

        for key, value in sorted(kwargs.items()):  # sort key for consistency
            if value:  # skip empty value
                key_parts.append(f"{key}:{value}")
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_cached_data(self, cache_key):  # get cached data from Redis
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set_cached_data(self, cache_key, data, ttl=None):  # set data in Redis cache
        try:
            ttl = ttl or self.default_ttl
            self.redis.setex(cache_key, ttl, json.dumps(data, default=str))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete_cached_data(self, pattern):  # delete cached data by pattern
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def flush_cache(self):  # clear entire cache
        try:
            self.redis.flushdb()
            return True
        except Exception as e:
            print(f"Cache flush error: {e}")
            return False

redis_client = redis.Redis(  # connect to Redis server
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)
cache_manager = CacheManager(redis_client)   # create cache manager instance

def cache_response(cache_key_prefix, ttl=300, user_specific=False):   # enhanced cache decorator
    """Enhanced cache decorator that properly handles query parameters"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_params = {}   # build cache parameters 
            
            if user_specific and hasattr(request, 'current_user'):  # add user-specific caching if needed
                cache_params['user_id'] = request.current_user.id

            query_params = request.args.to_dict()  # add all request query parameters to cache key
            cache_params.update(query_params)
            
            cache_key = cache_manager.generate_cache_key(cache_key_prefix, **cache_params)  # generate unique cache key

            # get cache
            cached_data = cache_manager.get_cached_data(cache_key)
            if cached_data:
                return make_response(cached_data, 200)

            # execute original function
            result = func(*args, **kwargs)

            # cache the result if successful 
            if (hasattr(result, 'status_code') and 
                result.status_code == 200 and 
                hasattr(result, 'is_json') and 
                result.is_json):
                
                response_data = result.get_json()
                cache_manager.set_cached_data(cache_key, response_data, ttl)

            return result
        return wrapper
    return decorator

# cache invalidation decorator 
def invalidate_cache(cache_patterns):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if hasattr(result, 'status_code') and result.status_code in [200, 201]:
                for pattern in cache_patterns:
                    cache_manager.delete_cached_data(pattern)
            return result
        return wrapper
    return decorator


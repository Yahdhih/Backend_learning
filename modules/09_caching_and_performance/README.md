# Module 09 — Caching & Performance

> The fastest query is the one that never runs. Caching is how you scale without rewriting everything.

---

## Learning Objectives

- Understand when and why to cache
- Use Redis as a cache backend
- Use Django's cache framework (per-view, per-object, low-level)
- Understand cache invalidation strategies
- Profile and fix slow queries

---

## 1. Why Cache?

```
Without cache:
  Request → Django → Database → Response   (50ms per request)
  1000 users/second = 1000 DB queries/second

With cache:
  Request → Django → Cache HIT → Response  (2ms per request)
                   → Cache MISS → Database → Cache SET → Response
  1000 users/second ≈ 10 DB queries/second (if 99% hit rate)
```

---

## 2. Redis

Redis is an in-memory data store. It's the standard cache backend for Django.

```bash
brew install redis
brew services start redis

# Test
redis-cli ping   # → PONG

# Install Python client
pip install redis django-redis
```

Configure Django to use Redis:
```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
```

---

## 3. Django Cache Framework

```python
from django.core.cache import cache

# Set a value (expires in 300 seconds)
cache.set("my_key", "my_value", timeout=300)

# Get (returns None if missing or expired)
value = cache.get("my_key")

# Get with default
value = cache.get("my_key", default="fallback")

# Delete
cache.delete("my_key")

# Cache a database query result
def get_popular_posts():
    cached = cache.get("popular_posts")
    if cached is not None:
        return cached
    posts = list(Post.objects.filter(published=True).order_by("-view_count")[:10])
    cache.set("popular_posts", posts, timeout=300)
    return posts

# Per-view caching
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # cache for 15 minutes
def popular_posts_view(request):
    ...

# Cache invalidation: delete when data changes
def publish_post(post_id):
    post = Post.objects.get(id=post_id)
    post.published = True
    post.save()
    cache.delete("popular_posts")  # invalidate
```

---

## 4. Cache Invalidation

**The hardest problem in computer science.** When cached data changes, when do you clear the cache?

Strategies:
1. **TTL-based**: let the cache expire naturally. Simple but data can be stale.
2. **Event-based**: clear the cache when the data changes. Correct but complex.
3. **Versioning**: don't invalidate — change the cache key. Old data becomes orphaned.

```python
# Versioning approach
def get_user_cache_key(user_id):
    version = cache.get(f"user_{user_id}_version", 0)
    return f"user_{user_id}_v{version}"

def invalidate_user_cache(user_id):
    # Increment version → old cached data becomes unreachable
    cache.incr(f"user_{user_id}_version", ignore_key_check=True)
```

---

## 5. Query Optimization

```python
# Use .only() to fetch only needed fields
posts = Post.objects.only("id", "title", "created_at")

# Use .defer() to exclude expensive fields
posts = Post.objects.defer("content")   # skip the big text column

# Use .values() when you don't need full model instances
post_data = Post.objects.values("id", "title")   # returns dicts, not objects

# Use .values_list() for flat lists
post_ids = Post.objects.values_list("id", flat=True)

# Bulk operations (single query instead of N)
Post.objects.bulk_create([
    Post(title="Post 1", ...),
    Post(title="Post 2", ...),
])

Post.objects.filter(published=False).update(published=True)  # 1 query
```

---

## Exercises

1. [Exercise 01 — Redis Basics](exercises/01_redis_basics.md)
2. [Exercise 02 — Cache Integration](exercises/02_cache_integration.md)
3. [Exercise 03 — Query Profiling](exercises/03_query_profiling.md)

---

## Next → [Module 10: Deployment](../10_deployment/README.md)

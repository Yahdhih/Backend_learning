# Module 06 — REST APIs with Django REST Framework

> DRF is the standard library for building APIs in Django. It handles serialization, validation, authentication, and routing — all the boilerplate you'd otherwise write by hand.

---

## Learning Objectives

- Understand REST constraints (not just "JSON over HTTP")
- Use DRF Serializers for validation and serialization
- Use ViewSets and Routers for clean API structure
- Add pagination and filtering
- Version an API

---

## 1. What Makes an API "RESTful"?

REST (Representational State Transfer) has 6 constraints:
1. **Client-Server** — clear separation of concerns
2. **Stateless** — each request contains all info needed; no server-side session
3. **Cacheable** — responses must define whether they can be cached
4. **Uniform Interface** — consistent URL structure, HTTP methods, responses
5. **Layered System** — client doesn't know if it talks to a proxy or the real server
6. **Code on Demand** (optional) — server can send executable code

Most "REST APIs" only follow constraints 1, 2, 4. That's fine in practice.

---

## 2. DRF Setup

```bash
pip install djangorestframework

# settings.py
INSTALLED_APPS = [
    ...
    "rest_framework",
]

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}
```

---

## 3. Serializers — The Core Concept

A Serializer does two things:
1. **Serialize**: Python object → JSON dict (for responses)
2. **Deserialize**: JSON dict → validated Python object (for requests)

```python
from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "title", "content", "author", "author_name",
                  "comment_count", "published", "created_at"]
        read_only_fields = ["id", "created_at", "author"]

    def get_comment_count(self, obj):
        return obj.comments.count()

    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters")
        return value

    def validate(self, data):
        # Cross-field validation
        if data.get("published") and not data.get("content"):
            raise serializers.ValidationError("Published posts must have content")
        return data
```

---

## 4. ViewSets and Routers

A ViewSet combines related views into one class. A Router auto-generates URLs.

```python
# views.py
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related("author").prefetch_related("tags")
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "view_count"]

    def perform_create(self, serializer):
        # Automatically set author to the logged-in user
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        post = self.get_object()
        post.published = True
        post.save()
        return Response({"status": "published"})

    @action(detail=False, methods=["get"])
    def my_posts(self, request):
        posts = Post.objects.filter(author=request.user)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

# urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("posts", PostViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
]
# Auto-generates:
# GET    /api/posts/           → list
# POST   /api/posts/           → create
# GET    /api/posts/42/        → retrieve
# PUT    /api/posts/42/        → update
# PATCH  /api/posts/42/        → partial_update
# DELETE /api/posts/42/        → destroy
# POST   /api/posts/42/publish/ → custom action
# GET    /api/posts/my_posts/  → custom action
```

---

## 5. Pagination

```python
# Custom pagination
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"  # ?page_size=50
    max_page_size = 100
    page_query_param = "page"           # ?page=2

# Response format:
# {
#   "count": 150,
#   "next": "http://api.example.com/posts/?page=3",
#   "previous": "http://api.example.com/posts/?page=1",
#   "results": [...]
# }
```

---

## Exercises

1. [Exercise 01 — First Serializer](exercises/01_first_serializer.md)
2. [Exercise 02 — ViewSets and Routers](exercises/02_viewsets.md)
3. [Exercise 03 — Filtering and Pagination](exercises/03_filtering.md)

---

## Next → [Module 07: Auth & Sessions](../07_auth_and_sessions/README.md)

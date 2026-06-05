# Exercise 02 — URL Routing & Views

Build a JSON API for blog posts — no templates, pure JSON responses.

---

## Part A: Wire Up URLs

**`blog_project/urls.py`:**
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("posts.urls")),
]
```

**Create `posts/urls.py`:**
```python
from django.urls import path
from . import views

urlpatterns = [
    path("posts/", views.post_list, name="post-list"),
    path("posts/<int:pk>/", views.post_detail, name="post-detail"),
]
```

---

## Part B: Write Function-Based Views

In `posts/views.py`, implement these:

```python
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Post


# TASK 1: Implement post_list
# GET  /api/posts/      → list all posts as JSON
# POST /api/posts/      → create a new post from JSON body
@csrf_exempt   # needed because we haven't set up CSRF tokens yet
def post_list(request):
    pass  # implement this


# TASK 2: Implement post_detail
# GET    /api/posts/1/  → return post 1
# PUT    /api/posts/1/  → replace post 1 with request body
# DELETE /api/posts/1/  → delete post 1
@csrf_exempt
def post_detail(request, pk):
    pass  # implement this
```

**Requirements:**
- GET list: return `{"posts": [...], "count": N}`
- POST create: validate `title` and `content` are present; return 400 with error if missing; return 201 with created post
- GET detail: return 404 with `{"error": "Not found"}` if post doesn't exist
- PUT: update title/content; return updated post
- DELETE: return 204 with empty body

**Test your implementation:**
```bash
# List posts
curl http://localhost:8000/api/posts/

# Create a post
curl -X POST http://localhost:8000/api/posts/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Post", "content": "Hello world"}'

# Get specific post
curl http://localhost:8000/api/posts/1/

# Update it
curl -X PUT http://localhost:8000/api/posts/1/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "content": "New content"}'

# Delete it
curl -X DELETE http://localhost:8000/api/posts/1/
```

---

## Part C: URL Parameters and Filtering

Add these routes to `posts/urls.py`:
```python
path("posts/search/", views.search_posts, name="post-search"),
path("posts/published/", views.published_posts, name="post-published"),
```

Implement the views:

```python
# GET /api/posts/search/?q=python
# Return posts where title or content contains the query
def search_posts(request):
    q = request.GET.get("q", "")
    # Hint: Post.objects.filter(title__icontains=q) | Post.objects.filter(content__icontains=q)
    # Or: Post.objects.filter(Q(title__icontains=q) | Q(content__icontains=q))
    # from django.db.models import Q
    pass


# GET /api/posts/published/
# Return only published=True posts
def published_posts(request):
    pass
```

---

## Part D: Class-Based Views (Rewrite)

Rewrite `post_list` and `post_detail` as class-based views.

```python
from django.views import View

class PostListView(View):
    def get(self, request):
        # same as GET in post_list
        pass

    def post(self, request):
        # same as POST in post_list
        pass


class PostDetailView(View):
    def get(self, request, pk):
        pass

    def put(self, request, pk):
        pass

    def delete(self, request, pk):
        pass
```

Update `urls.py` to use `.as_view()`:
```python
path("posts/", views.PostListView.as_view()),
path("posts/<int:pk>/", views.PostDetailView.as_view()),
```

**Question:** What does `.as_view()` do? Why is it needed?

---

## Part E: Custom Error Responses

Django returns HTML error pages by default. Override them to return JSON.

In `posts/views.py`:
```python
def custom_404(request, exception):
    return JsonResponse({"error": "Not found"}, status=404)

def custom_500(request):
    return JsonResponse({"error": "Internal server error"}, status=500)
```

In `blog_project/urls.py`:
```python
handler404 = "posts.views.custom_404"
handler500 = "posts.views.custom_500"
```

Test: `curl -v http://localhost:8000/api/nonexistent/`

---

## Checkpoint Questions

1. Why does `request.POST` not work for JSON bodies? What should you use instead?
2. What does `@csrf_exempt` do? Why is it only needed during development without a frontend?
3. What is the difference between `JsonResponse(data)` and `HttpResponse(json.dumps(data))`?
4. What does `Post.objects.get(pk=pk)` raise when the post doesn't exist? How should you handle it?

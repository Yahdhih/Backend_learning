# Project 01 — Blog API

**Prerequisites:** Complete Modules 00–06

**Time estimate:** 4–6 hours

---

## What You'll Build

A production-quality REST API for a blog platform.

**Features:**
- Users can register, login, logout
- Authenticated users can create/edit/delete their own posts
- Posts have tags (many-to-many)
- Anyone can read published posts
- Authors can add comments
- Pagination on all list endpoints
- Search posts by title or content
- Filter posts by tag or author

---

## Data Model

```
User (Django built-in)
  │
  ├──< Post >── Tag (M2M)
  │    ├── title: CharField
  │    ├── content: TextField
  │    ├── published: BooleanField
  │    ├── view_count: IntegerField
  │    └── created_at: DateTimeField
  │
  └──< Comment
       ├── post: FK → Post
       ├── content: TextField
       └── created_at: DateTimeField
```

---

## Required API Endpoints

```
Auth:
  POST   /api/auth/register/          Create account
  POST   /api/auth/login/             Get JWT token pair
  POST   /api/auth/token/refresh/     Refresh access token
  POST   /api/auth/logout/            Blacklist refresh token

Posts:
  GET    /api/posts/                  List published posts (paginated)
  POST   /api/posts/                  Create post (auth required)
  GET    /api/posts/{id}/             Get a post (increments view_count)
  PUT    /api/posts/{id}/             Replace post (author only)
  PATCH  /api/posts/{id}/             Update fields (author only)
  DELETE /api/posts/{id}/             Delete (author only)
  POST   /api/posts/{id}/publish/     Publish post (author only)

  GET    /api/posts/?search=python    Search
  GET    /api/posts/?tag=django       Filter by tag
  GET    /api/posts/?author=alice     Filter by author

Tags:
  GET    /api/tags/                   List all tags
  GET    /api/tags/{slug}/posts/      Posts for a tag

Comments:
  GET    /api/posts/{id}/comments/    List comments
  POST   /api/posts/{id}/comments/    Add comment (auth required)
  DELETE /api/posts/{id}/comments/{comment_id}/  Delete (author only)

Me:
  GET    /api/me/                     Current user profile
  GET    /api/me/posts/               My posts (including drafts)
```

---

## Step-by-Step Guide

### 1. Project setup
```bash
django-admin startproject blog_api .
python manage.py startapp posts
python manage.py startapp accounts
pip install djangorestframework djangorestframework-simplejwt django-filter
```

### 2. Models
Define models in `posts/models.py` following the schema above.

### 3. Serializers
- `UserSerializer` (registration)
- `PostListSerializer` (compact, for lists)
- `PostDetailSerializer` (full, for detail view)
- `CommentSerializer`
- `TagSerializer`

### 4. ViewSets
- `PostViewSet` with custom actions: `publish`, `my_posts`
- `CommentViewSet` nested under posts
- `TagViewSet`

### 5. Authentication
Use `djangorestframework-simplejwt` for JWT.

### 6. Permissions
Write `IsAuthorOrReadOnly`.

### 7. Filtering and search
Use `django-filter` for tag/author filtering.

---

## Acceptance Criteria

- [ ] All endpoints return correct status codes
- [ ] Unauthenticated users can only read published posts
- [ ] Authors can only edit/delete their own content
- [ ] Pagination works on all list endpoints
- [ ] Search and filter work correctly
- [ ] No N+1 queries (use select_related/prefetch_related)
- [ ] Invalid input returns 400 with descriptive errors
- [ ] Posting to a nonexistent resource returns 404

---

## Testing

Write tests using Django's `TestCase`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

class PostAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("alice", password="pass")

    def test_create_post_requires_auth(self):
        response = self.client.post("/api/posts/", {"title": "Test", "content": "Content"})
        self.assertEqual(response.status_code, 401)

    def test_create_post_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/posts/", {"title": "Test", "content": "Content"})
        self.assertEqual(response.status_code, 201)
```

Run: `python manage.py test`

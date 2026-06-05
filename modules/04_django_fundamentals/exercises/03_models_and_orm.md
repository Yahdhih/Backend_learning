# Exercise 03 — Models and ORM

Build a more realistic data model: Users, Posts, Tags, and Comments.

---

## Part A: Define the Models

In `posts/models.py`, build this schema:

```
User (Django's built-in) ──< Post >── Tag (many-to-many)
                                │
                                └──< Comment
```

```python
from django.db import models
from django.contrib.auth.models import User  # use Django's built-in User


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)   # url-friendly: "python-tips"

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"
```

```bash
python manage.py makemigrations posts
python manage.py sqlmigrate posts 0002   # read the SQL
python manage.py migrate
```

---

## Part B: ORM Queries in the Shell

```bash
python manage.py shell
```

Practice these queries. For each one, think about what SQL it generates.

```python
from django.contrib.auth.models import User
from posts.models import Post, Tag, Comment

# Create test data
user1 = User.objects.create_user("alice", "alice@test.com", "password")
user2 = User.objects.create_user("bob", "bob@test.com", "password")

tag_py = Tag.objects.create(name="Python", slug="python")
tag_dj = Tag.objects.create(name="Django", slug="django")
tag_db = Tag.objects.create(name="Database", slug="database")

p1 = Post.objects.create(title="Django ORM Guide", content="...", author=user1, published=True)
p1.tags.add(tag_py, tag_dj)

p2 = Post.objects.create(title="SQL Basics", content="...", author=user1, published=True)
p2.tags.add(tag_db)

p3 = Post.objects.create(title="Draft Post", content="...", author=user2)

Comment.objects.create(post=p1, author=user2, content="Great post!")
Comment.objects.create(post=p1, author=user1, content="Thanks!")
Comment.objects.create(post=p2, author=user2, content="Very helpful")

# ── TASK: Write the ORM query for each of these ──────────────────────────────

# 1. All published posts
published = Post.objects.filter(published=True)

# 2. Posts by user1
user1_posts = Post.objects.filter(author=user1)

# 3. Posts tagged with "python"
python_posts = Post.objects.filter(tags__slug="python")

# 4. Posts with MORE THAN ONE comment
from django.db.models import Count
busy_posts = Post.objects.annotate(comment_count=Count("comments")).filter(comment_count__gt=1)

# 5. The number of published posts per user
# Expected: {"alice": 2, "bob": 0} or similar
per_user = (
    User.objects
    .annotate(post_count=Count("posts", filter=Q(posts__published=True)))
    .values("username", "post_count")
)

# 6. All tags used by alice's posts
alice_tags = Tag.objects.filter(posts__author=user1).distinct()

# 7. Posts ordered by comment count (most commented first)
by_comments = Post.objects.annotate(n=Count("comments")).order_by("-n")

# 8. Get p1 and its author without an extra query (select_related)
# Without select_related: accessing p1.author makes a 2nd DB query
# With select_related: fetched in one JOIN query
p = Post.objects.select_related("author").get(id=p1.id)
print(p.author.username)   # no extra query

# 9. Get all posts with their tags loaded (prefetch_related for M2M)
posts_with_tags = Post.objects.prefetch_related("tags").all()
for p in posts_with_tags:
    print(p.tags.all())    # no extra queries per post

# 10. Increment view_count atomically (without race condition)
from django.db.models import F
Post.objects.filter(id=p1.id).update(view_count=F("view_count") + 1)
```

---

## Part C: The N+1 Problem

This is one of the most common performance bugs in Django.

```python
# BAD: N+1 queries
# This makes 1 query for all posts, then 1 query PER POST for the author
posts = Post.objects.all()   # 1 query
for post in posts:
    print(post.author.username)  # 1 query × N posts = N+1 total!

# GOOD: select_related (JOIN)
# Makes 1 query total using SQL JOIN
posts = Post.objects.select_related("author").all()
for post in posts:
    print(post.author.username)  # no extra queries

# BAD: N+1 with many-to-many
posts = Post.objects.all()
for post in posts:
    print(post.tags.all())  # 1 query per post!

# GOOD: prefetch_related (2 queries total)
posts = Post.objects.prefetch_related("tags").all()
for post in posts:
    print(post.tags.all())  # no extra queries
```

**Task:** Turn on query logging to SEE this happening.

Add to `settings.py`:
```python
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
        }
    },
}
```

Now run both versions in the shell and count the SQL queries.

---

## Part D: Write the Query

Given this data, write ORM queries to answer each question:

1. Find all users who have never written a post
2. Find the post with the most comments
3. Find all posts that have no tags
4. Find all tags that have been used in more than 2 posts
5. Find the average number of comments per published post

<details>
<summary>Answers (try first)</summary>

```python
from django.db.models import Count, Avg, Q

# 1. Users with no posts
User.objects.filter(posts__isnull=True)

# 2. Post with most comments
Post.objects.annotate(n=Count("comments")).order_by("-n").first()

# 3. Posts with no tags
Post.objects.filter(tags__isnull=True)

# 4. Tags used in more than 2 posts
Tag.objects.annotate(post_count=Count("posts")).filter(post_count__gt=2)

# 5. Average comments per published post
Post.objects.filter(published=True).annotate(
    n=Count("comments")
).aggregate(avg=Avg("n"))
```
</details>

---

## Checkpoint Questions

1. What SQL does `Post.objects.filter(author__username="alice")` generate? (Use `python manage.py shell` and add `from django.db import connection; print(connection.queries)` after the query)
2. What is the difference between `on_delete=CASCADE` and `on_delete=SET_NULL`? When would you use each?
3. What happens if you access `post.tags.all()` 100 times in a loop without `prefetch_related`?
4. Why is `F("view_count") + 1` safer than `post.view_count + 1` when incrementing a counter?

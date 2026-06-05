# Module 05 — Databases & The ORM

> The database is where your data lives forever. Understanding SQL makes you a dramatically better Django developer.

---

## Learning Objectives

- Write raw SQL: SELECT, JOIN, GROUP BY, subqueries, indexes
- Understand transactions and ACID guarantees
- Use Django's ORM for complex queries
- Write and manage migrations safely
- Identify and fix the N+1 problem
- Understand database indexes and when to use them

---

## 1. Why Learn SQL if Django Has an ORM?

Three reasons:
1. **Debugging**: when your ORM query is slow or wrong, you need to read the SQL
2. **Complex queries**: some queries are much simpler in SQL than ORM
3. **Migrations**: production schema changes can destroy data if you're not careful

---

## 2. SQL Crash Course (Read Before Exercises)

```sql
-- SELECT
SELECT id, name, email FROM users WHERE active = true ORDER BY name LIMIT 10;

-- JOIN (combine rows from two tables)
SELECT posts.title, users.name
FROM posts
JOIN users ON posts.author_id = users.id
WHERE posts.published = true;

-- LEFT JOIN (include rows even if no match)
SELECT users.name, COUNT(posts.id) as post_count
FROM users
LEFT JOIN posts ON posts.author_id = users.id
GROUP BY users.id, users.name
ORDER BY post_count DESC;

-- Subquery
SELECT * FROM posts
WHERE author_id IN (
    SELECT id FROM users WHERE active = true
);

-- Insert
INSERT INTO posts (title, content, author_id, created_at)
VALUES ('Hello', 'Content', 1, NOW());

-- Update
UPDATE posts SET published = true WHERE id = 5;

-- Delete
DELETE FROM posts WHERE published = false AND created_at < NOW() - INTERVAL '30 days';
```

---

## 3. PostgreSQL Setup

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14
brew services start postgresql@14

# Create a database
createdb blog_dev

# Connect
psql blog_dev

# In psql:
\dt          -- list tables
\d users     -- describe a table
\q           -- quit
```

Update `settings.py` to use PostgreSQL:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "blog_dev",
        "USER": "your_username",
        "PASSWORD": "",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

---

## 4. Indexes

An index makes queries fast by pre-sorting data.

```python
# Add an index on a field
class Post(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    email = models.EmailField(unique=True)  # unique implies an index

    class Meta:
        indexes = [
            # Composite index for queries that filter by both
            models.Index(fields=["author", "published"], name="post_author_published_idx"),
        ]
```

**Rule of thumb:** Add an index on any field you filter by frequently. But indexes slow down writes, so don't add them blindly.

---

## 5. Transactions

A transaction is a group of operations that either ALL succeed or ALL fail.

```python
from django.db import transaction

# Method 1: atomic block
with transaction.atomic():
    order = Order.objects.create(user=user, total=100)
    Payment.objects.create(order=order, amount=100)
    user.balance -= 100
    user.save()
# If ANY line above fails, ALL changes are rolled back

# Method 2: decorator
@transaction.atomic
def process_payment(user, amount):
    ...

# Savepoints: nested transactions
with transaction.atomic():
    do_important_thing()
    try:
        with transaction.atomic():     # savepoint
            do_risky_thing()           # if this fails...
    except Exception:
        pass                           # ...only this inner block rolls back
    do_another_thing()                 # this still runs
```

---

## Exercises

1. [Exercise 01 — Raw SQL First](exercises/01_raw_sql.md)
2. [Exercise 02 — Complex ORM Queries](exercises/02_complex_orm.md)
3. [Exercise 03 — Migrations Deep Dive](exercises/03_migrations.md)
4. [Exercise 04 — The N+1 Problem](exercises/04_n_plus_one.md)

---

## Next → [Module 06: REST APIs with DRF](../06_rest_apis_drf/README.md)

"""
Exercise 03 — Decorators Lab

Django uses decorators everywhere. This exercise builds 6 decorators
from scratch that mirror real Django/DRF behavior.

Run with: python3 03_decorators_lab.py
"""

import time
import functools
from typing import Callable


# ─── 1. @timer ────────────────────────────────────────────────────────────────
# Measures and prints how long the decorated function takes to run.
#
# @timer
# def slow():
#     time.sleep(0.1)
#
# slow()  # prints: "slow took 0.102s"

def timer(func: Callable) -> Callable:
    # YOUR CODE HERE
    pass


# ─── 2. @retry(n) ────────────────────────────────────────────────────────────
# Retries the function up to n times if it raises an exception.
# If it still fails after n tries, raise the last exception.
#
# @retry(3)
# def flaky():
#     if random.random() < 0.7:
#         raise ConnectionError("network error")
#     return "ok"

def retry(n: int):
    # YOUR CODE HERE
    pass


# ─── 3. @require_method("GET", "POST") ───────────────────────────────────────
# Simulates Django's @require_http_methods decorator.
# Our "request" is just a dict with a "method" key.
# If the method isn't allowed, return {"error": "Method Not Allowed"} with status 405.
#
# @require_method("GET")
# def view(request):
#     return {"data": "ok"}, 200
#
# view({"method": "POST"})   → ({"error": "Method Not Allowed"}, 405)
# view({"method": "GET"})    → ({"data": "ok"}, 200)

def require_method(*allowed_methods: str):
    # YOUR CODE HERE
    pass


# ─── 4. @cache(seconds) ──────────────────────────────────────────────────────
# Caches the result for `seconds` seconds.
# Uses the function arguments as the cache key.
# After the TTL expires, recomputes.
#
# @cache(seconds=2)
# def expensive(n):
#     time.sleep(0.5)
#     return n * n

def cache(seconds: int):
    # YOUR CODE HERE
    pass


# ─── 5. @validate_json(*required_keys) ───────────────────────────────────────
# Our "request body" is a dict. Checks that all required keys are present.
# If any are missing, return ({"error": "Missing fields: ..."}, 400)
# Otherwise call the function normally.
#
# @validate_json("name", "email")
# def create_user(body):
#     return {"created": body["name"]}, 201
#
# create_user({"name": "Alice"})              → ({"error": "Missing fields: email"}, 400)
# create_user({"name": "Alice", "email": "a@b.com"}) → ({"created": "Alice"}, 201)

def validate_json(*required_keys: str):
    # YOUR CODE HERE
    pass


# ─── 6. @log_calls ───────────────────────────────────────────────────────────
# Logs every call: function name, arguments, return value, and any exception.
# Format:
#   CALL add(1, 2) → 3
#   CALL divide(1, 0) → RAISED ZeroDivisionError: division by zero

def log_calls(func: Callable) -> Callable:
    # YOUR CODE HERE
    pass


# ─── COMPOSE THEM ─────────────────────────────────────────────────────────────
#
# Real Django views stack multiple decorators. Order matters.
# When decorators are stacked, they apply bottom-up:
#
#   @decorator_a
#   @decorator_b
#   def view():
#       ...
#
# is equivalent to: view = decorator_a(decorator_b(view))
# So decorator_b wraps view first, then decorator_a wraps the result.

@log_calls
@require_method("GET", "POST")
@validate_json("title", "content")
def create_post(request, body):
    return {"created": body["title"]}, 201


# ─── TESTS ───────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}")
            print(f"    Expected: {expected!r}")
            print(f"    Got:      {actual!r}")
            failed += 1

    def check_raises(name, fn, exc):
        nonlocal passed, failed
        try:
            fn()
            print(f"  ✗ {name} (no exception)")
            failed += 1
        except exc:
            print(f"  ✓ {name}")
            passed += 1

    print("\n─── 1. @timer ───")
    @timer
    def fast():
        return 42

    result = fast()
    check("timer returns value", result, 42)
    # Can't easily check the print output, just verify it doesn't break

    print("\n─── 2. @retry ───")
    attempt = [0]

    @retry(3)
    def sometimes_fails():
        attempt[0] += 1
        if attempt[0] < 3:
            raise RuntimeError("not yet")
        return "ok"

    result = sometimes_fails()
    check("retry eventually succeeds", result, "ok")
    check("retry attempts count", attempt[0], 3)

    @retry(2)
    def always_fails():
        raise ValueError("always")

    check_raises("retry gives up after n", always_fails, ValueError)

    print("\n─── 3. @require_method ───")
    @require_method("GET")
    def get_only(request):
        return {"data": "ok"}, 200

    response, status = get_only({"method": "GET"})
    check("allowed method passes", status, 200)

    response, status = get_only({"method": "POST"})
    check("blocked method returns 405", status, 405)
    check("blocked method error key", "error" in response, True)

    print("\n─── 4. @cache ───")
    call_count = [0]

    @cache(seconds=1)
    def slow_add(a, b):
        call_count[0] += 1
        return a + b

    slow_add(1, 2)
    slow_add(1, 2)
    slow_add(1, 2)
    check("cache prevents repeated calls", call_count[0], 1)
    slow_add(1, 3)
    check("different args not cached", call_count[0], 2)

    time.sleep(1.1)
    slow_add(1, 2)
    check("cache expires after TTL", call_count[0], 3)

    print("\n─── 5. @validate_json ───")
    @validate_json("name", "email")
    def make_user(body):
        return {"user": body["name"]}, 201

    response, status = make_user({"name": "Alice", "email": "a@a.com"})
    check("valid body passes", status, 201)

    response, status = make_user({"name": "Alice"})
    check("missing field returns 400", status, 400)
    check("error mentions missing field", "email" in response["error"], True)

    print("\n─── 6. @log_calls ───")
    @log_calls
    def add(a, b):
        return a + b

    result = add(2, 3)
    check("log_calls returns value", result, 5)

    @log_calls
    def boom():
        raise ZeroDivisionError("oops")

    check_raises("log_calls reraises exception", boom, ZeroDivisionError)

    print(f"\nResults: {passed} passed, {failed} failed")


if __name__ == "__main__":
    run_tests()

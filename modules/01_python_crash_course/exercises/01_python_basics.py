"""
Exercise 01 — Python Basics

Fill in each function. Run with: python3 01_python_basics.py
Tests at the bottom will tell you if you got it right.
"""


# ─── PART 1: Data Structures ──────────────────────────────────────────────────

def flatten(nested_list: list) -> list:
    """
    Given a list of lists, return a single flat list.

    flatten([[1, 2], [3, 4], [5]]) → [1, 2, 3, 4, 5]

    Hint: use a list comprehension with two for clauses.
    """
    # YOUR CODE HERE
    pass


def invert_dict(d: dict) -> dict:
    """
    Swap keys and values.

    invert_dict({"a": 1, "b": 2}) → {1: "a", 2: "b"}

    Hint: dict comprehension
    """
    # YOUR CODE HERE
    pass


def group_by(items: list, key: str) -> dict:
    """
    Group a list of dicts by a key.

    users = [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob",   "role": "user"},
        {"name": "Carol", "role": "admin"},
    ]
    group_by(users, "role") →
    {
        "admin": [{"name": "Alice", ...}, {"name": "Carol", ...}],
        "user":  [{"name": "Bob", ...}]
    }
    """
    # YOUR CODE HERE
    pass


# ─── PART 2: String Manipulation ─────────────────────────────────────────────

def to_snake_case(name: str) -> str:
    """
    Convert CamelCase to snake_case.

    to_snake_case("HelloWorld")      → "hello_world"
    to_snake_case("myHTTPSRequest")  → "my_https_request"

    Hint: iterate over characters, check isupper()
    """
    # YOUR CODE HERE
    pass


def parse_query_string(qs: str) -> dict:
    """
    Parse a URL query string into a dict.

    parse_query_string("page=2&limit=10&active=true")
    → {"page": "2", "limit": "10", "active": "true"}

    parse_query_string("")
    → {}
    """
    # YOUR CODE HERE
    pass


# ─── PART 3: Functions ───────────────────────────────────────────────────────

def memoize(func):
    """
    Decorator that caches function results.

    The first call with a given argument computes the result.
    Subsequent calls with the same argument return the cached result.

    Hint: use a dict as a cache inside the wrapper.
    """
    # YOUR CODE HERE
    pass


def pipeline(*functions):
    """
    Create a function that applies functions left to right.

    double = lambda x: x * 2
    add_one = lambda x: x + 1
    square = lambda x: x ** 2

    pipe = pipeline(double, add_one, square)
    pipe(3)  →  double(3)=6, add_one(6)=7, square(7)=49
    """
    # YOUR CODE HERE
    pass


# ─── PART 4: File-like Operations ────────────────────────────────────────────

def read_csv_to_dicts(csv_text: str) -> list:
    """
    Parse a CSV string into a list of dicts.
    First row is headers.

    csv_text = '''name,age,role
    Alice,30,admin
    Bob,25,user'''

    Returns:
    [
        {"name": "Alice", "age": "30", "role": "admin"},
        {"name": "Bob",   "age": "25", "role": "user"}
    ]

    No importing csv module — do it manually with split().
    """
    # YOUR CODE HERE
    pass


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
            print(f"    Expected: {expected}")
            print(f"    Got:      {actual}")
            failed += 1

    print("\n─── Part 1: Data Structures ───")
    check("flatten basic", flatten([[1, 2], [3, 4], [5]]), [1, 2, 3, 4, 5])
    check("flatten empty", flatten([[], [], [1]]), [1])
    check("invert_dict basic", invert_dict({"a": 1, "b": 2}), {1: "a", 2: "b"})
    users = [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "user"},
        {"name": "Carol", "role": "admin"},
    ]
    grouped = group_by(users, "role")
    check("group_by admin count", len(grouped["admin"]), 2)
    check("group_by user count", len(grouped["user"]), 1)

    print("\n─── Part 2: Strings ───")
    check("snake_case hello_world", to_snake_case("HelloWorld"), "hello_world")
    check("snake_case my_http_request", to_snake_case("MyHTTPRequest"), "my_http_request")
    check("parse_query_string", parse_query_string("page=2&limit=10"), {"page": "2", "limit": "10"})
    check("parse_query_string empty", parse_query_string(""), {})

    print("\n─── Part 3: Functions ───")
    call_count = [0]
    @memoize
    def slow_square(n):
        call_count[0] += 1
        return n * n
    slow_square(5)
    slow_square(5)
    slow_square(5)
    check("memoize caches", call_count[0], 1)
    check("memoize correct", slow_square(4), 16)

    double = lambda x: x * 2
    add_one = lambda x: x + 1
    square = lambda x: x ** 2
    pipe = pipeline(double, add_one, square)
    check("pipeline", pipe(3), 49)

    print("\n─── Part 4: CSV ───")
    csv = "name,age\nAlice,30\nBob,25"
    result = read_csv_to_dicts(csv)
    check("csv length", len(result), 2)
    check("csv first row", result[0], {"name": "Alice", "age": "30"})
    check("csv second row", result[1], {"name": "Bob", "age": "25"})

    print(f"\nResults: {passed} passed, {failed} failed")


if __name__ == "__main__":
    run_tests()

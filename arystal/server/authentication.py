"""Authentication hook. There are no accounts yet: every request is accepted as the local user.

Every route of the API depends on `authenticate`, so adding real authentication later (tokens, accounts) means replacing this
one function, not rewriting the routes. It works for HTTP requests and WebSockets alike.
"""

from fastapi.requests import HTTPConnection

LOCAL_USER = "local"


def authenticate(connection: HTTPConnection) -> str:
    """Return the name of the user making the request. Today: always the local user.

    To add authentication, read credentials from `connection.headers` (or the query string for WebSockets),
    check them, and raise fastapi.HTTPException(401) when they are wrong.
    """
    return LOCAL_USER

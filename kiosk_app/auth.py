from functools import wraps
from typing import Any, Callable

from flask import redirect, session, url_for


def login_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrap(*args: Any, **kwargs: Any) -> Any:
        if "admin" not in session:
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)

    return wrap

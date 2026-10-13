"""What HTTP clients learn about server-side exceptions.

Exception messages routinely carry file paths, connection strings or fragments of
data, so by default a client only gets a generic message with an error id; the
full exception (with traceback) is logged server-side under that same id, so an
operator can find it from what the client reports.

``expose_errors=True`` (on ``qh.mk_app``, ``qh.base.mk_fastapi_app``, ...) restores
the old behaviour of sending the exception text to the client; use it for
development or when every client is trusted.

>>> detail = error_detail(ValueError('/secret/path'), context='f')
>>> '/secret/path' in detail, detail.startswith('Internal error in f (error id: ')
(False, True)
>>> error_detail(ValueError('/secret/path'), context='f', expose_errors=True)
'Error in f: /secret/path'
"""

import logging
from typing import Optional
from uuid import uuid4

logger = logging.getLogger("qh")

DFLT_EXPOSE_ERRORS = False


def error_detail(
    exc: BaseException,
    *,
    context: str,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
    exposed_text: Optional[str] = None,
) -> str:
    """Log ``exc`` (with traceback) under a fresh error id and return the text to
    send to the client.

    Args:
        exc: The exception raised while serving the request.
        context: What failed (typically the function name); shown to the client.
        expose_errors: If True, the client gets the exception text.
        exposed_text: The client-facing text when ``expose_errors`` is True;
            defaults to ``f"Error in {context}: {exc}"``.
    """
    error_id = uuid4().hex
    logger.error("Error in %s (error id: %s)", context, error_id, exc_info=exc)
    if expose_errors:
        return (
            exposed_text if exposed_text is not None else f"Error in {context}: {exc}"
        )
    return f"Internal error in {context} (error id: {error_id})"

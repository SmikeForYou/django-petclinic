"""Resolve a stable per-caller identity at the MCP event boundary.

If the request carries an authenticated principal, that identity is
used. Otherwise a server-issued, persistent pseudonymous identifier is
minted and bound to the caller via a signed cookie. Only the SHA-256
hash of that identity is retained in the deduplication store; no raw
identifier ever leaves the system.
"""
import hashlib
import logging
import uuid
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

COOKIE_NAME = 'mcp_cid'
COOKIE_SALT = 'metering'
# ~400 days, which is also the maximum lifetime most browsers accept.
COOKIE_MAX_AGE = 34560000


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def resolve_caller_identity(request) -> Tuple[str, Optional[str]]:
    """Return ``(identity_hash, cookie_to_set_or_None)``.

    * If ``request.user`` is authenticated, the identity is
      ``user:<pk>`` and no cookie needs to be minted.
    * Otherwise the signed cookie ``mcp_cid`` is read. If present and
      valid, its value is reused. If absent or tampered with, a new
      UUID4 hex value is minted and returned as ``cookie_to_set`` so
      the view can attach it to the response.

    Only the hash leaves this module. Different anonymous callers
    always receive distinct identifiers (no collapsing to a single
    anonymous id).
    """
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return _sha256('user:{}'.format(user.pk)), None

    cookie_value: Optional[str] = None
    try:
        cookie_value = request.get_signed_cookie(
            COOKIE_NAME, default=None, salt=COOKIE_SALT
        )
    except Exception:
        # Tampered or expired signature -> treat as absent.
        cookie_value = None

    cookie_to_set: Optional[str] = None
    if not cookie_value:
        cookie_value = uuid.uuid4().hex
        cookie_to_set = cookie_value

    return _sha256('anon:{}'.format(cookie_value)), cookie_to_set

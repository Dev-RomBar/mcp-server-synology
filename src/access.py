"""Fork: Cloudflare Access JWT check (defence in depth behind the Access-protected tunnel).

Every request that passed the origin's Access application carries a signed
``Cf-Access-Jwt-Assertion`` header. Verifying it here means that reaching the container
port directly, without going through Cloudflare, gets nothing.
"""

import json

import anyio
import jwt
from starlette.types import ASGIApp, Receive, Scope, Send

HEADER = b"cf-access-jwt-assertion"


class AccessJwtVerifier:
    def __init__(self, team_domain: str, audience: str) -> None:
        self.issuer = f"https://{team_domain}"
        self.audience = audience
        self._jwks = jwt.PyJWKClient(f"{self.issuer}/cdn-cgi/access/certs", cache_keys=True)

    def verify(self, token: str) -> dict:
        key = self._jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iat", "aud", "iss"]},
        )


class AccessJwtMiddleware:
    """Reject HTTP requests without a valid Access JWT, except on ``exempt_paths``."""

    def __init__(
        self, app: ASGIApp, verifier: AccessJwtVerifier, exempt_paths: frozenset[str]
    ) -> None:
        self.app = app
        self.verifier = verifier
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.exempt_paths:
            await self.app(scope, receive, send)
            return
        token = dict(scope["headers"]).get(HEADER, b"").decode()
        try:
            if not token:
                raise jwt.InvalidTokenError("missing Cf-Access-Jwt-Assertion")
            # PyJWKClient fetches keys with blocking I/O: keep it off the event loop.
            await anyio.to_thread.run_sync(self.verifier.verify, token)
        except (jwt.PyJWTError, jwt.PyJWKClientError):
            await _forbidden(send)
            return
        await self.app(scope, receive, send)


async def _forbidden(send: Send) -> None:
    body = json.dumps({"error": "forbidden"}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})

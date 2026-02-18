import json
from base64 import b64decode
from typing import override

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from jwcrypto import jwk, jwt
from jwcrypto.common import json_decode
from jwcrypto.jws import InvalidJWSObject, InvalidJWSSignature
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings

EXCLUDED_PATHS = {"/docs", "/redoc", "/api/v1/openapi.json"}


class KeycloakAuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: set[str] | None = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths

    @override
    async def dispatch(self, request: Request, call_next):
        # NOTE: Skip OPTIONS (CORS preflight) and excluded paths
        if request.method == "OPTIONS" or request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        try:
            token = self._get_bearer_token(request)
            decoded_token = self._decode_token(token=token)
            print(decoded_token)

            request.state.user = {"email": decoded_token.get("email")}

            response = await call_next(request)
            return response
        except HTTPException as err:
            return JSONResponse(
                status_code=err.status_code, content={"detail": err.detail}
            )
        except (InvalidJWSSignature, InvalidJWSObject):
            return JSONResponse(
                status_code=401, content={"detail": "JWT Signature Verification failed"}
            )
        except jwt.JWTExpired as err:
            return JSONResponse(
                status_code=401, content={"detail": f"Expired Token provided - {err}"}
            )

    def _get_bearer_token(self, request: Request) -> str:
        """
        Extracts and validates the Bearer token from the Authorization header.

        Returns:
            str: The Bearer token if valid.

        Raises:
            UnauthorizedError: If the token is missing or invalid.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token_parts = auth_header.split()
        if len(token_parts) != 2 or token_parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="malformed auth token")

        return token_parts[1]

    def _decode_token(self, token: str, **kwargs):
        """
        Decode user token.
        more info at https://tools.ietf.org/html/rfc7517

        :param token: Keycloak token
        :param kwargs: Additional keyword arguments for jwcrypto's JWT object
        :returns: Decoded token
        """
        if settings.BYPASS_AUTH_SIG_CHECK:
            token_payload = token.split(".")[1]
            if not len(token_payload) % 4 == 0:
                token_payload += "==="

            decoded_token = b64decode(token_payload)
            data = json.loads(decoded_token)
            return data

        public_key: str = (
            "-----BEGIN PUBLIC KEY-----\n"
            + settings.KEYCLOAK_PUBLIC_KEY
            + "\n-----END PUBLIC KEY-----"
        )
        json_web_key = jwk.JWK.from_pem(public_key.encode("utf-8"))

        try:
            full_jwt = jwt.JWT(jwt=token, **kwargs)
        except ValueError as err:
            raise HTTPException(
                status_code=401, detail="Invalid keycloak token"
            ) from err

        # leeway refers to the amount of time tolerance allowed when checking
        # the validity of time-based claims in the token
        ONE_MINUTE_IN_SECONDS = 60  # pylint: disable=invalid-name
        full_jwt.leeway = ONE_MINUTE_IN_SECONDS

        full_jwt.validate(json_web_key)
        return json_decode(full_jwt.claims)

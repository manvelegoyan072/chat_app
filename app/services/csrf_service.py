import secrets
import hmac
import os
from fastapi import HTTPException

class CSRFService:
    def __init__(self):
        self.secret = os.getenv("CSRF_SECRET", "your-csrf-secret")

    def generate_csrf_token(self, session_id: str) -> str:

        token = secrets.token_urlsafe(32)
        signature = hmac.new(
            self.secret.encode(),
            (session_id + token).encode(),
            digestmod="sha256"
        ).hexdigest()
        return f"{token}:{signature}"

    def verify_csrf_token(self, session_id: str, csrf_token: str) -> bool:

        try:
            token, signature = csrf_token.split(":")
            expected_signature = hmac.new(
                self.secret.encode(),
                (session_id + token).encode(),
                digestmod="sha256"
            ).hexdigest()
            return hmac.compare_digest(signature.encode(), expected_signature.encode())
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
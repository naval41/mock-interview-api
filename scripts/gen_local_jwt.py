"""Generate a local JWT for testing protected endpoints.

Usage:
    ENV=local python scripts/gen_local_jwt.py [user_id] [hours]

Prints a bearer token signed with the app's configured jwt_secret_key.
The only claim the API requires is `userId` (see app/core/security.py).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from jose import jwt

# Ensure project root is importable when run as `python scripts/gen_local_jwt.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

user_id = sys.argv[1] if len(sys.argv) > 1 else "local-test-user"
hours = int(sys.argv[2]) if len(sys.argv) > 2 else 12

payload = {
    "userId": user_id,
    "exp": datetime.now(timezone.utc) + timedelta(hours=hours),
}
token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
print(token)

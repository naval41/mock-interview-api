"""Shared pytest configuration and fixtures for the mock-interview-api suite.

The suite is designed to be **hermetic**: it imports application modules without
touching a real database, external API, or any secret. `app.core.config.Settings`
has required fields (``database_url``, ``jwt_secret_key``) and
``app.core.database`` builds a SQLAlchemy engine at import time, so we inject
dummy values into the environment *before* any application module is imported.
The engine is created lazily and never connects, so no database is required.
"""

import os

# Populate the mandatory settings BEFORE application modules are imported.
# `setdefault` keeps any real values a developer may already have exported.
_TEST_ENV_DEFAULTS = {
    "ENV": "local",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "JWT_SECRET_KEY": "test-secret-not-used",
    "ENVIRONMENT": "test",
    # Empty external credentials keep clients in their no-op/uninitialized state.
    "GOOGLE_API_KEY": "",
    "DEEPGRAM_API_KEY": "",
    "AWS_ACCESS_KEY_ID": "",
    "AWS_SECRET_ACCESS_KEY": "",
    "SQS_INTERVIEW_COMPLETION_QUEUE_URL": "",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

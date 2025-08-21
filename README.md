# Mock Interview API

A FastAPI-based skeleton application with CRUD operations, following best practices for enterprise applications.

## Features

- **Layered Architecture**: Model-Controller-Service-DAO pattern
- **Async/Await**: Full async support with SQLModel and PostgreSQL
- **JWT Authentication**: Secure token-based authentication
- **Comprehensive Logging**: Structured logging with request/response AOP
- **Environment Management**: Separate configurations for local/production
- **Database Pool**: Async connection pooling with SQLModel
- **CORS Support**: Configurable cross-origin resource sharing
- **API Documentation**: Auto-generated OpenAPI/Swagger docs
- **Error Handling**: Centralized exception handling
- **Security**: Password hashing, JWT validation middleware

## Project Structure

```
app/
├── core/           # Core configurations and utilities
├── models/         # SQLModel database models
├── dao/            # Data Access Objects
├── services/       # Business logic layer
├── controllers/    # FastAPI route handlers
├── middleware/     # Custom middleware (logging, etc.)
├── schemas/        # Pydantic request/response schemas
└── main.py         # Application entry point
```

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   - Copy and modify `config/local.env` with your database settings
   - Set `ENV=local` for development or `ENV=production` for production

3. **Database Setup**
   - Ensure PostgreSQL is running
   - Update database URL in the environment file
   - Tables will be created automatically on startup

4. **Run Application**
   ```bash
   # Development
   ENV=local python -m uvicorn app.main:app --reload
   
   # Production
   ENV=production python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/logout` - Logout

### Validate User (JWT)
- `GET /api/v1/auth/validate` - Validate a user by JWT token

**How to call:**
Send the JWT token in the `Authorization` header as a Bearer token.

Example using curl:
```sh
curl -X GET http://localhost:8000/api/v1/auth/validate \
  -H "Authorization: Bearer <your-jwt-token-here>"
```

If the token is valid and the user exists, you will receive user info. Otherwise, you will get a 401 error.

### Products (CRUD Example)
- `POST /api/v1/products/` - Create product
- `GET /api/v1/products/` - List all products
- `GET /api/v1/products/{id}` - Get specific product
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product
- `GET /api/v1/products/category/{category}` - Products by category
- `GET /api/v1/products/search?name={name}` - Search products
- `GET /api/v1/products/my-products` - Get user's products

### Health & Info
- `GET /` - API info
- `GET /health` - Health check
- `GET /docs` - API documentation (local only)

## Environment Variables

Key environment variables in `config/*.env`:

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT token signing
- `JWT_EXPIRE_MINUTES` - Token expiration time
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT` - Runtime environment (local, production)
- `CORS_ORIGINS` - Allowed CORS origins

## Authentication Flow

1. Register: `POST /auth/register` with email, username, password
2. Login: `POST /auth/login` with email and password
3. Use returned JWT token in Authorization header: `Bearer <token>`
4. All product endpoints require authentication

## Logging

The application uses structured logging with:
- Request/response AOP logging
- Database operation logging
- Error tracking with request IDs
- JSON formatted logs for production

## Development

- API docs available at `/docs` in local environment
- All routes have proper error handling and logging
- Async/await pattern used throughout
- Type hints and Pydantic validation
- Modular, testable architecture

## Database Models

- **Users**: Authentication and user management
- **Products**: Sample CRUD entity with categories and stock
- Foreign key relationships properly configured
- UUID primary keys for better security

## Security Features

- Password hashing with bcrypt
- JWT token validation middleware
- User ownership validation for CRUD operations
- Request/response logging for audit trails
- CORS protection
- SQL injection prevention via SQLModel
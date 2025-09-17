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

### Interview Management
- `POST /api/start-interview` - Start an interview session
- `POST /api/offer` - Handle WebRTC offer for interview connection
- `POST /api/inject-problem` - Inject problem context into interview
- `POST /api/inject-custom-context` - Inject custom context into interview
- `GET /api/status/{room_id}` - Get interview session status
- `GET /api/connections/status` - Get all connection statuses

### Interview Timer Control
- `POST /api/interview/{room_id}/timer/start` - Start interview timer
- `POST /api/interview/{room_id}/timer/pause` - Pause interview timer
- `POST /api/interview/{room_id}/timer/reset` - Reset interview timer
- `GET /api/interview/{room_id}/timer/status` - Get detailed timer status

### Real-time Events (Server-Sent Events)
- `GET /api/interview/{room_id}/events` - SSE stream for real-time interview updates

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

## Interview System Features

### Real-time Interview Management
- **WebRTC Integration**: Real-time audio/video communication using Pipecat
- **Phase-based Interviews**: Structured interview phases with automatic transitions
- **Timer Management**: Configurable timers for each interview phase
- **Context Switching**: Dynamic instruction injection based on interview phases
- **Real-time Notifications**: Server-Sent Events for frontend updates

### Interview Timer System
The interview system includes a sophisticated timer management system:

- **Automatic Phase Transitions**: Timers automatically transition between interview phases
- **Pause/Resume Support**: Interview timers can be paused and resumed
- **Progress Tracking**: Real-time progress updates with remaining time
- **Phase Context**: Each phase can have custom instructions and duration
- **Completion Handling**: Automatic interview finalization when all phases complete

## Server-Sent Events (SSE) Integration

### Overview
The application provides real-time updates to frontend clients using Server-Sent Events (SSE). This allows the backend to push notifications about interview phase changes, timer updates, and other events directly to connected clients.

### SSE Endpoint
```
GET /api/interview/{room_id}/events
```

### Event Types
The SSE stream sends the following event types:

1. **`connected`** - Initial connection established
2. **`phase_started`** - First interview phase begins
3. **`phase_changed`** - Interview phase transition occurred
4. **`interview_completed`** - All interview phases finished
5. **`heartbeat`** - Connection keep-alive (every 30 seconds)
6. **`error`** - Server-side errors

### Testing SSE Implementation

#### 1. Basic SSE Connection Test
```bash
# Connect to SSE stream (replace room_id with your interview room)
curl -N -H "Accept: text/event-stream" \
  http://localhost:8000/api/interview/interview-playground/events
```

**Expected Response:**
```
event: connected
data: {"room_id": "interview-playground", "timestamp": "2025-09-15T10:30:00"}

event: heartbeat
data: {"timestamp": "2025-09-15T10:30:30", "room_id": "interview-playground"}
```

#### 2. Full Interview Flow Test

**Step 1: Start an Interview Session**
```bash
curl -X POST http://localhost:8000/api/start-interview \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "interview-playground",
    "mock_interview_id": "your-mock-interview-id",
    "user_id": "your-user-id"
  }'
```

**Step 2: Connect to SSE Stream (in separate terminal)**
```bash
curl -N -H "Accept: text/event-stream" \
  http://localhost:8000/api/interview/interview-playground/events
```

**Step 3: Monitor Phase Changes**
As the interview timer progresses, you'll see events like:

```
event: phase_started
data: {"sequence": 1, "question_id": "q1", "duration_minutes": 15, "instructions": "System design phase...", "timestamp": "2025-09-15T10:30:45"}

event: phase_changed
data: {"new_sequence": 2, "previous_sequence": 1, "question_id": "q2", "duration_minutes": 20, "instructions": "Coding phase...", "transition_count": 1, "timestamp": "2025-09-15T10:45:45"}

event: interview_completed
data: {"total_transitions": 2, "session_duration_seconds": 2100, "session_duration_minutes": 35, "total_planner_fields": 3, "timestamp": "2025-09-15T11:05:45"}
```

#### 3. Timer Status Monitoring
```bash
# Check current timer status
curl http://localhost:8000/api/interview/interview-playground/timer/status
```

**Response:**
```json
{
  "success": true,
  "room_id": "interview-playground",
  "timer_status": {
    "is_running": true,
    "is_paused": false,
    "current_sequence": 1,
    "remaining_time_seconds": 720,
    "elapsed_time_seconds": 180,
    "progress_percentage": 20.0
  },
  "interview_context": {
    "current_planner": {
      "sequence": 1,
      "question_id": "q1",
      "duration": 15,
      "question_type": "system_design"
    },
    "total_planner_fields": 3
  }
}
```

### Frontend Integration

#### JavaScript/TypeScript Example
```javascript
// Connect to SSE stream
const eventSource = new EventSource('/api/interview/interview-playground/events');

// Handle phase changes
eventSource.addEventListener('phase_changed', (event) => {
    const data = JSON.parse(event.data);
    console.log('New interview phase:', data);
    
    // Update UI
    updatePhaseIndicator(data.new_sequence);
    showPhaseChangeNotification({
        sequence: data.new_sequence,
        questionId: data.question_id,
        duration: data.duration_minutes,
        instructions: data.instructions
    });
});

// Handle interview completion
eventSource.addEventListener('interview_completed', (event) => {
    const data = JSON.parse(event.data);
    console.log('Interview completed:', data);
    showCompletionModal(data);
});

// Handle connection errors
eventSource.onerror = (event) => {
    console.error('SSE connection error:', event);
    // Implement reconnection logic
};
```

#### React Hook Example
```typescript
import { useEffect, useState } from 'react';

function useInterviewSSE(roomId: string) {
    const [currentPhase, setCurrentPhase] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');

    useEffect(() => {
        const eventSource = new EventSource(`/api/interview/${roomId}/events`);
        
        eventSource.onopen = () => setConnectionStatus('connected');
        eventSource.onerror = () => setConnectionStatus('error');
        
        eventSource.addEventListener('phase_changed', (event) => {
            const data = JSON.parse(event.data);
            setCurrentPhase(data);
        });
        
        return () => eventSource.close();
    }, [roomId]);

    return { currentPhase, connectionStatus };
}
```

### Troubleshooting SSE

#### Common Issues:

1. **"Interview bot not found" Error**
   - Ensure you've started an interview session first
   - Check that the room_id matches your active session

2. **No Phase Events**
   - Verify that the interview timer is running
   - Check that planner fields are properly configured
   - Monitor server logs for timer events

3. **Connection Drops**
   - SSE includes automatic heartbeat every 30 seconds
   - Implement reconnection logic in your frontend
   - Check firewall/proxy settings for SSE support

#### Debug Commands:
```bash
# Check active connections
curl http://localhost:8000/api/connections/status

# Check specific room status
curl http://localhost:8000/api/status/interview-playground

# Monitor server logs for SSE events
tail -f server.log | grep -E "(SSE|Timer|Phase)"
```

### SSE vs WebSocket Comparison

| Feature | SSE | WebSocket |
|---------|-----|-----------|
| **Direction** | Server → Client | Bidirectional |
| **Complexity** | Simple | More Complex |
| **Reconnection** | Automatic | Manual |
| **Firewall Support** | Better | Can be blocked |
| **Resource Usage** | Lower | Higher |
| **Use Case** | Notifications | Real-time chat |

**Recommendation**: Use SSE for interview phase notifications as it's simpler, more reliable, and perfect for one-way server-to-client communication.
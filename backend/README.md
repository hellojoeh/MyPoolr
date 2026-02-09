# MyPoolr Circles Backend

Backend API for MyPoolr Circles savings group management system.

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase and Redis credentials
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## Development

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=.
```

### Background Tasks
```bash
# Start Celery worker
celery -A celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A celery_app beat --loglevel=info
```

## API Endpoints

### MyPoolr Management
- `POST /mypoolr/create` - Create new savings group
- `GET /mypoolr/{id}` - Get MyPoolr by ID
- `GET /mypoolr/admin/{admin_id}` - Get admin's MyPoolrs

### Member Management
- `POST /member/join` - Join MyPoolr group
- `GET /member/{id}` - Get member by ID
- `GET /member/mypoolr/{mypoolr_id}` - Get group members

### Transaction Management
- `POST /transaction/create` - Create transaction
- `POST /transaction/confirm` - Confirm transaction
- `GET /transaction/mypoolr/{mypoolr_id}` - Get group transactions

### System
- `GET /` - API information
- `GET /health` - Health check

## Architecture

The backend follows a modular architecture:

- **API Layer**: FastAPI routers for HTTP endpoints
- **Models**: Pydantic models for data validation
- **Database**: Supabase integration with connection management
- **Tasks**: Celery background tasks for automation
- **Config**: Environment-based configuration management

## Requirements Fulfilled

This backend foundation supports:
- **Requirement 10.1**: Background task processing with Celery
- **Requirement 10.2**: Reliable task execution with retry mechanisms
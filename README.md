# GroundZero

GroundZero is an AI-powered browser extension that provides intelligent content analysis and recommendations using machine learning and external data sources.

## Project Structure

```
/server           - FastAPI backend server
  /routers        - API route handlers
  /oracles        - External data source integrations
    /finance      - Financial data oracle
    /tech         - Technology data oracle
    /fallback     - Fallback data sources
  /ml             - Machine learning models and utilities
  /data           - Data storage and caching
  /schemas        - Pydantic models for API validation
/extension        - Browser extension
  /src            - Extension source code
/docs             - Documentation
/tests            - Test suites
```

## Setup

### Prerequisites
- Python 3.9+
- Node.js 16+ (for extension development)

### Installation

1. Install Python dependencies:
```bash
pip install -e .
```

2. For development with additional tools:
```bash
pip install -e ".[dev]"
```

### Running the Server

Start the FastAPI development server:
```bash
cd server
python main.py
```

Or using uvicorn directly:
```bash
uvicorn server.main:app --reload
```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Development

This is the initial boilerplate setup. Implementation of features is pending.

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## License

TBD

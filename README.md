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

### Running Tests

Run the complete test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=server --cov-report=html
```

Run linter:
```bash
ruff check server/ tests/
```

### Manual QA

Run the manual QA script to test the /check_claim endpoints:
```bash
bash manual_qa.sh
```

### API Endpoints

#### Core Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

#### Claim Checking (PR5)
- `POST /check_claim/parse` - Parse and classify a claim
  - Input: `{"claim_text": "SOL jumped 8% after ETF approval this morning."}`
  - Output: Extracted claim information and domain classification
  
- `POST /check_claim/check` - Full fact-checking pipeline
  - Input: `{"claim_text": "SOL jumped 8% after ETF approval this morning."}`
  - Output: Aggregated verdict from multiple oracles with confidence and evidence

### Oracle System (PR5)

The fact-checking pipeline uses a multi-oracle architecture:

**Router Logic:**
- Routes claims to domain-specific oracles based on classification
- finance → FinanceOracle
- tech_release → TechReleaseOracle  
- general → LLMOracle
- Triggers LLM fallback if domain confidence < 0.6 OR primary verdict is uncertain
- Never falls back when primary oracle is already LLM

**Aggregation Rules:**
- If any oracle returns `likely_false` → final verdict is `likely_false`
- Else if any oracle returns `likely_true` → final verdict is `likely_true`
- Else → final verdict is `uncertain`
- Confidence: min for conflicts, average for support, 0.3 for all uncertain
- `unsupported` verdicts are treated as `uncertain`

**Implemented Oracles:**
- **FinanceOracle**: Validates price movement claims using cached market data
  - Uses forward-only timestamp snapping to avoid look-ahead bias
  - Computes pre/post event returns and abnormal volume metrics
  - Checks percentage mismatch between claim and actual movement
- **TechReleaseOracle**: Stub implementation (returns uncertain)
- **LLMOracle**: Stub implementation used as fallback (returns uncertain)

## License

TBD

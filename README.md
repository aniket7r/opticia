# gemini3

Real-time visual understanding AI platform with voice guidance. Built for Google DeepMind Gemini 3 Hackathon.

## Vision

"ChatGPT that can see" — AI assistant that understands what you're looking at through your camera and guides you with natural voice conversation.

## Tech Stack

- **Frontend**: Next.js 15 (App Router, React 19)
- **Backend**: FastAPI + Python 3.11
- **AI**: Google Gemini Live API
- **Database**: Supabase
- **Deployment**: Google Cloud Run

## Project Structure

```
gemini3/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # REST endpoints
│   │   ├── ws/       # WebSocket handlers
│   │   ├── services/ # Business logic
│   │   ├── models/   # Pydantic schemas
│   │   ├── core/     # Config, logging
│   │   └── prompts/  # System prompts
│   └── tests/
├── frontend/         # Next.js frontend
│   └── src/
└── shared/           # Shared types/constants
```

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your settings
npm run dev
```

## API Endpoints

- `GET /api/v1/health` - Health check

## License

MIT

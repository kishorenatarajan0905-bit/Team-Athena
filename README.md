# InPlant - AI-Powered Personalized Learning Path Recommender

An intelligent learning assistant that recommends personalized learning paths based on a learner's interests, goals, previous learning history, and skill level.

## Features

- **Conversational Interface**: Chat with an AI learning coach to describe goals in natural language
- **Learner Profiling**: Captures interests, experience level, completed courses, and objectives
- **Smart Recommendations**: Suggests relevant courses, projects, and learning resources using vector similarity search
- **Structured Learning Paths**: Generates roadmaps with prerequisites and milestones (Foundation → Core → Specialization → Capstone)
- **AI Explanations**: Explains why each recommendation was made and answers learner queries
- **Progress Dashboard**: Visualizes skill development, milestones, and next recommended actions

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL + pgvector** - Database with vector similarity search
- **SQLAlchemy 2.0** - Async ORM
- **NVIDIA Nemotron 3 Ultra** - LLM for reasoning and chat
- **NVIDIA NV-Embed-v1** - Embeddings for semantic search
- **JWT Authentication** - Secure auth

### Frontend
- **React 18 + TypeScript** - Type-safe UI
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **TanStack Query** - Server state management
- **Recharts** - Data visualization
- **React Router** - Client-side routing

## Quick Start

### Prerequisites
- Docker & Docker Compose
- NVIDIA API Key (provided)

### 1. Clone and Configure
```bash
git clone <repository-url>
cd inplant
cp .env.example .env
# Edit .env with your NVIDIA API key
```

### 2. Start with Docker Compose
```bash
docker-compose up -d --build
```

This starts:
- PostgreSQL with pgvector on port 5432
- Backend API on http://localhost:8000
- Frontend on http://localhost:5173

### 3. Seed Database (Optional)
```bash
# Run seed script to populate courses
docker-compose exec backend python seed_data.py
```

### 4. Access the Application
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Demo Login: `demo@inplant.ai` / `demo1234`

## Local Development (Without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env .env
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database
```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name inplant-postgres \
  -e POSTGRES_USER=inplant \
  -e POSTGRES_PASSWORD=inplant_dev \
  -e POSTGRES_DB=inplant \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

## Project Structure

```
inplant/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Config, DB, security, NVIDIA client
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   │   ├── embeddings.py      # Embedding utilities
│   │   │   ├── profiling.py       # Learner profiling engine
│   │   │   ├── recommendation.py  # Recommendation engine
│   │   │   ├── path_generator.py  # Learning path generator
│   │   │   └── ai_assistant.py    # AI assistant with tools
│   │   └── main.py       # FastAPI app
│   ├── seed_data.py      # Course seeding script
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   │   ├── Chat.tsx          # Conversational interface
│   │   │   ├── Dashboard.tsx     # Progress dashboard
│   │   │   ├── PathView.tsx      # Learning path visualization
│   │   │   ├── Recommendations.tsx # Course recommendations
│   │   │   └── Profile.tsx       # Learner profile
│   │   ├── hooks/        # Custom React hooks
│   │   ├── services/     # API client
│   │   ├── types/        # TypeScript types
│   │   └── utils/        # Helper functions
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login, returns JWT

### Profile
- `GET /api/profile` - Get learner profile
- `PUT /api/profile` - Update profile
- `POST /api/profile/analyze` - Analyze natural language goals

### Recommendations
- `GET /api/recommendations` - Get personalized recommendations
- `GET /api/recommendations/{course_id}/explain` - Explain recommendation

### Learning Paths
- `POST /api/paths/generate` - Generate learning path
- `GET /api/paths` - List user's paths
- `GET /api/paths/{path_id}` - Get path with nodes
- `PATCH /api/paths/{path_id}/nodes/{node_id}` - Mark node complete
- `GET /api/paths/{path_id}/next` - Get next recommended actions

### Chat
- `POST /api/chat` - Conversational interface

### Dashboard
- `GET /api/dashboard` - Aggregated progress data

## Architecture

### Learner Profiling Engine
Parses natural language goals via LLM into structured profile:
- Interests, experience level, goals, target role
- Time commitment, learning style
- Generates skill embedding for similarity search

### Recommendation Engine
Hybrid scoring combining:
- **Semantic similarity** (50%): Course embeddings ↔ learner skill embeddings
- **Difficulty match** (20%): Appropriate challenge level
- **Prerequisite satisfaction** (30%): Ready to start

### Learning Path Generator
- Topological sort on prerequisite graph
- Milestone assignment: Foundation → Core → Specialization → Capstone
- Adaptive sequencing based on available hours/week

### AI Assistant
LLM with tool calling for:
- Profile analysis
- Recommendations with reasoning
- Path generation and navigation
- Progress tracking and adaptation

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | NVIDIA API key for LLM/embeddings | Required |
| `NVIDIA_BASE_URL` | NVIDIA API base URL | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_CHAT_MODEL` | Chat model name | `nvidia/nemotron-3-ultra` |
| `NVIDIA_EMBED_MODEL` | Embedding model name | `nvidia/nv-embed-v1` |
| `DATABASE_URL` | PostgreSQL connection string | Auto-configured in Docker |
| `JWT_SECRET` | JWT signing secret | Required |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

## Deployment

### Docker Compose (Production)
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Cloud Deployment
- **Render**: Connect GitHub repo, add environment variables
- **Railway**: Deploy from GitHub, add PostgreSQL plugin
- **Fly.io**: `fly launch` with Dockerfile

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- NVIDIA for Nemotron 3 Ultra and NV-Embed models
- pgvector for PostgreSQL vector similarity search
- FastAPI, React, and Tailwind CSS communities
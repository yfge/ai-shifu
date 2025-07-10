# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Shifu is a guide powered by LLM that provides AI-led chat flows where humans follow the conversation rather than leading it. Unlike traditional chatbots, AI-Shifu maintains an AI-controlled storyline while allowing users to ask questions and interact at any time. The system makes personalized output based on user identity, interests, and preferences.

## Architecture

This is a multi-service application with the following components:

### Backend API (`src/api/`)
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: MySQL with Redis for caching
- **Language**: Python 3.11
- **Key Services**:
  - `shifu/`: Core AI conversation logic and course management
  - `study/`: User learning session management and interaction handling
  - `lesson/`: Course content and script management
  - `user/`: User authentication and profile management
  - `order/`: Payment and subscription handling
  - `llm/`: LLM integration (OpenAI, Baidu, etc.)

### Frontend Web (`src/web/`)
- **Framework**: React 18 with TypeScript
- **Build Tool**: Craco (Create React App Configuration Override)
- **State Management**: Zustand
- **UI Library**: Ant Design + Ant Design Mobile
- **Internationalization**: i18next

### Course Editor (`src/cook-web/`)
- **Framework**: Next.js 15 with TypeScript
- **UI Library**: Radix UI + Tailwind CSS
- **Features**: Course creation, script editing, and content management

## Common Development Commands

### API Development
```bash
cd src/api
pip install -r requirements.txt
flask db upgrade
gunicorn -w 4 -b 0.0.0.0:5800 'app:app' --timeout 300 --log-level debug
```

### Web Development
```bash
cd src/web
pnpm install
pnpm run start:dev        # Development server
pnpm run build           # Production build
pnpm run test            # Run tests
pnpm run lint:knip       # Dead code elimination
```

### Cook-Web Development
```bash
cd src/cook-web
npm install
npm run dev              # Development server
npm run build           # Production build
npm run lint            # ESLint with max 0 warnings
```

## Database Management

The project uses Flask-Migrate for database migrations:
- Migration files are in `src/api/migrations/versions/`
- Run migrations with `flask db upgrade`
- Create new migrations with `flask db migrate -m "description"`

## Key Data Models

### Core Models
- `AICourse`: Course/scenario definitions
- `AILesson`: Individual lessons within courses
- `AILessonScript`: Script content for lessons
- `AICourseLessonAttendScript`: User interaction logs
- `FavoriteScenario`: User favorites
- `AiCourseAuth`: Course authorization management

### User Management
- Multi-language support (zh-CN, en-US)
- Phone/email authentication
- User profiles with preferences

## LLM Integration

The system supports multiple LLM providers:
- OpenAI (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
- Baidu Ernie
- Zhipu GLM
- Configurable via environment variables

## Environment Setup

Key environment variables:
- `DEFAULT_LLM_MODEL`: Primary LLM model
- `DEFAULT_LLM_TEMPERATURE`: LLM temperature setting
- `SQLALCHEMY_DATABASE_URI`: Database connection
- `REDIS_HOST`/`REDIS_PORT`: Redis configuration
- `REACT_APP_BASEURL`: Frontend API endpoint

## Development Workflow

1. **API Changes**: Update models in `src/api/flaskr/service/*/models.py`
2. **Frontend Changes**: Components in `src/web/src/Components/` and `src/web/src/Pages/`
3. **Course Editor**: Components in `src/cook-web/src/components/`
4. **Testing**: Use `src/api/tests/` for API tests
5. **Internationalization**: Update JSON files in `public/locales/`

## Docker Development

Use `docker/docker-compose.yml` for containerized development:
- `ai-shifu-api`: Backend API service
- `ai-shifu-web`: Frontend web service
- `ai-shifu-cook-web`: Course editor service
- `ai-shifu-mysql`: MySQL database
- `ai-shifu-redis`: Redis cache
- `ai-shifu-nginx`: Reverse proxy

## Legacy Note

The `Legacy/` directory contains the old Streamlit-based course editor, which is being replaced by the Next.js cook-web application.
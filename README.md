# Ethera AI Assessment

Inventory & Order Management System built with React, FastAPI, PostgreSQL, Docker, and Docker Compose.

## Features
- Product CRUD with unique SKU and stock control
- Customer CRUD with unique email
- Order creation with inventory validation and automatic stock update
- Order cancellation restores stock
- React dashboard to manage products, customers, and orders
- Full containerization with Docker Compose

## Getting Started
1. Copy environment variables
   ```bash
   cp .env.example .env
   ```
2. Start services
   ```bash
   docker compose up --build
   ```
3. Open the apps
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000`

## Backend
- FastAPI app in `backend/app`
- Uses PostgreSQL database
- API docs: `http://localhost:8000/docs`

## Frontend
- React app in `frontend`
- Communicates with backend via `REACT_APP_API_URL`

## Docker
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `backend/.dockerignore`
- `frontend/.dockerignore`
- `pgdata` named volume for Postgres persistence

## Deployment Guidance
- Backend: deploy to Railway, Render, or Fly.io using the `backend/Dockerfile`
- Frontend: deploy to Netlify or Vercel using the `frontend` build
- For frontend deployment, Netlify can use `frontend/netlify.toml`
- Set `REACT_APP_API_URL` in frontend hosting to your live backend URL

## Notes
- Use `.env` for local secret configuration
- Do not commit `.env` to Git

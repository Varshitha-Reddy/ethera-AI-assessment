# Ethera AI — Inventory & Order Management System

Full-stack Inventory & Order Management System built with React, FastAPI, PostgreSQL, Docker, and Docker Compose.

## Live URLs

| Service | URL |
|---|---|
| Frontend | _deployed on Netlify — add URL here_ |
| Backend API | _deployed on Render — add URL here_ |
| Docker Hub | _add image URL here_ |

## Features

- Product CRUD with unique SKU and stock control
- Customer CRUD with unique email validation
- Order creation with inventory validation and automatic stock deduction
- Order cancellation restores stock automatically
- Auto-calculated order totals
- React dashboard — products, customers, orders, low-stock alerts
- Full containerization with Docker Compose

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React 18, Nginx (production)
- **Database:** PostgreSQL 16
- **Containers:** Docker, Docker Compose

## Local Development

### Prerequisites

- Docker and Docker Compose installed

### Start locally

```bash
cp .env.example .env
docker compose up --build
```

Open:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

## Deployment

### Backend — Render (one-click via render.yaml)

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Blueprint**.
3. Connect the GitHub repo — Render reads `render.yaml` automatically and creates the backend service and a managed PostgreSQL database.
4. Copy the deployed backend URL (e.g. `https://ethera-backend.onrender.com`).

### Frontend — Netlify

1. Go to [netlify.com](https://netlify.com) → **Add new site** → **Import from Git**.
2. Select the repo, set **Base directory** to `frontend/`.
3. Build command: `npm run build` | Publish directory: `build` (already in `netlify.toml`).
4. Under **Site configuration → Environment variables**, add:
   ```
   REACT_APP_API_URL=https://your-render-backend-url.onrender.com
   ```
5. Trigger a redeploy.

### Docker Hub (backend image)

```bash
docker build -t <your-dockerhub-username>/ethera-backend:latest ./backend
docker push <your-dockerhub-username>/ethera-backend:latest
```

## API Reference

### Products

| Method | Endpoint | Description |
|---|---|---|
| POST | `/products` | Create product |
| GET | `/products` | List all products |
| GET | `/products/{id}` | Get product by ID |
| PUT | `/products/{id}` | Update product |
| DELETE | `/products/{id}` | Delete product |

### Customers

| Method | Endpoint | Description |
|---|---|---|
| POST | `/customers` | Create customer |
| GET | `/customers` | List all customers |
| GET | `/customers/{id}` | Get customer by ID |
| DELETE | `/customers/{id}` | Delete customer |

### Orders

| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders` | Create order |
| GET | `/orders` | List all orders |
| GET | `/orders/{id}` | Get order by ID |
| DELETE | `/orders/{id}` | Cancel order (restores stock) |

## Business Rules

- Product SKU must be unique
- Customer email must be unique
- Product quantity cannot be negative
- Orders are rejected if any item has insufficient stock
- Creating an order automatically deducts stock
- Cancelling an order restores stock
- Order total is calculated automatically by the backend

## Docker

| File | Purpose |
|---|---|
| `backend/Dockerfile` | Python 3.12-slim, uvicorn |
| `frontend/Dockerfile` | Node 20-alpine build → nginx:alpine |
| `docker-compose.yml` | Orchestrates all three services |
| `render.yaml` | Render Blueprint for backend + managed DB |
| `frontend/netlify.toml` | Netlify build config |

PostgreSQL data is persisted in the `pgdata` named volume.

## Notes

- Never commit `.env` to Git
- `REACT_APP_API_URL` is a build-time variable — set it in your hosting platform's environment variables before deploying the frontend

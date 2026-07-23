FROM python:3.11

# Install Node.js + WeasyPrint system deps (Pango/Cairo/GDK-Pixbuf via libgobject).
# Required by US-125 Renderer (WeasyPrint) used by /api/simulation/<id>/export-pdf
# (US-133), /api/admin/reports/<id>/preview|generate|approve (US-128/129),
# /api/models/<slug>/pdf-brief (US-088 si bascule WeasyPrint plus tard).
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       nodejs npm \
       libpango-1.0-0 libpangoft2-1.0-0 \
       libharfbuzz0b \
       libcairo2 libgdk-pixbuf-2.0-0 \
       libffi-dev shared-mime-info \
       fonts-dejavu-core \
       ghostscript \
       poppler-utils \
  && rm -rf /var/lib/apt/lists/*

# Copy uv from the official uv image
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# The Twitter recommender is part of the simulation runtime, not an optional
# first-run download. Keep it in a deterministic image layer so production
# never waits on Hugging Face after a user starts a simulation.
ENV HF_HOME=/opt/huggingface

# Copy dependency descriptor files first to leverage Docker cache
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install dependencies (Node + Python)
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# Public model preloaded at build time. Runtime loading is local-only.
RUN cd backend \
  && uv run python -c "from transformers import AutoModel, AutoTokenizer; model = 'Twitter/twhin-bert-base'; AutoTokenizer.from_pretrained(model); AutoModel.from_pretrained(model)"

# Copy project source code
COPY . .

# Build the frontend bundle to frontend/dist (minified, tree-shaken, gzip+brotli)
# `vite preview` ensuite sert ce bundle static + SPA fallback.
RUN npm run build

EXPOSE 3000 5001

# Production : Flask backend (port 5001) + vite preview (static dist sur 3000,
# proxy /api → backend, SPA fallback intégré).
CMD ["npm", "run", "start"]

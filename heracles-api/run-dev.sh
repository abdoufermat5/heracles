#!/bin/bash
# =============================================================================
# Heracles API Development Server
# =============================================================================
# Start the API server for local development

set -e

cd "$(dirname "$0")"

# Check if .env exists, copy from example if not
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

echo "🚀 Starting Heracles API..."
echo "   URL: http://localhost:${API_PORT:-8000}"
echo "   Docs: http://localhost:${API_PORT:-8000}/api/docs"
echo ""

# Run with uvicorn
exec uvicorn heracles_api.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --reload \
    --reload-dir heracles_api

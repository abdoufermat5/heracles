# Heracles UI Dockerfile
# ======================

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files for caching
COPY heracles-ui/package*.json /app/

# Install dependencies
RUN npm ci

# Copy application code
COPY heracles-ui /app

# Create non-root user
RUN adduser -D -u 1000 heracles
RUN chown -R heracles:heracles /app
USER heracles

# Expose port
EXPOSE 5173

# Default command
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

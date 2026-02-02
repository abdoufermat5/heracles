# Build stage
FROM oven/bun:1 AS builder

WORKDIR /app

# Copy package files
COPY heracles-ui/package.json heracles-ui/bun.lock* ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source files
COPY heracles-ui/ .

# Build the application
RUN bun run build

# Production stage - nginx
FROM nginx:alpine

# Copy custom nginx config
COPY heracles-ui/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

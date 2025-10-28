FROM node:20-slim

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Create working directory and set permissions
# node:20-slim already has 'node' user with UID 1000
WORKDIR /workspace
RUN chown node:node /workspace

# Switch to non-root user
USER node

# Health check
HEALTHCHECK CMD claude --version || exit 1

# Default command shows version
CMD ["claude", "--version"]

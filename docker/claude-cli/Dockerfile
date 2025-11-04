FROM node:20-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    ca-certificates \
    openssh-client \
    rsync \
    jq \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Python development tools and app dependencies
RUN pip3 install --no-cache-dir --break-system-packages \
    black==24.10.0 \
    flake8==7.1.1 \
    pytest==8.3.4 \
    pytest-cov==6.0.0 \
    pytest-mock==3.15.1 \
    isort==5.13.2 \
    pyyaml==6.0.2 \
    safetensors==0.4.3 \
    python-dotenv==1.0.1 \
    flask==3.1.0 \
    flask-cors==5.0.0 \
    flask-login==0.6.3 \
    flask-sqlalchemy==3.1.1 \
    flask-talisman==1.1.0 \
    authlib==1.4.0 \
    requests==2.32.3 \
    jsonschema==4.23.0 \
    celery==5.4.0 \
    redis==5.2.1

# Prepare shared node_modules cache (used by remediation bootstrap)
RUN mkdir -p /opt/imagineer/node_modules && \
    npm install --prefix /opt/imagineer @rollup/rollup-linux-x64-gnu@latest && \
    chown -R node:node /opt/imagineer

# node:20-slim already has 'node' user with UID 1000, use it as worker
# Create working directories
RUN mkdir -p /workspace/repo /workspace/context /workspace/artifacts /workspace/logs \
    && chown -R node:node /workspace

# Set up SSH directory for node user
RUN mkdir -p /home/node/.ssh \
    && chown -R node:node /home/node/.ssh \
    && chmod 700 /home/node/.ssh

# Configure Git to use SSH
RUN git config --system core.sshCommand "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

WORKDIR /workspace

# Switch to node user (acts as worker)
USER node

# Health check
HEALTHCHECK CMD claude --version && python3 --version && git --version && gh --version || exit 1

# Default command (will be overridden by agent_runner.py at runtime)
CMD ["/bin/bash"]

# Dockerfile for Agent Skills Sandbox
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
    ca-certificates \
    gnupg \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Claude CLI refuses --dangerously-skip-permissions as root)
RUN useradd -m -s /bin/bash sandbox

# Add local bin to PATH for Claude CLI
ENV PATH="/home/sandbox/.local/bin:$PATH"

# Install Node.js 20.x (required for Claude CLI and pptxgenjs)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install pptxgenjs globally for PowerPoint generation
RUN npm install -g pptxgenjs

# Install Claude CLI via npm
RUN npm install -g @anthropic-ai/claude-code@latest

# Pre-create Claude CLI directories
RUN mkdir -p /home/sandbox/.claude/skills && chown -R sandbox:sandbox /home/sandbox/.claude

# Install Python dependencies (useful packages for skill execution)
RUN pip install --no-cache-dir \
    anthropic \
    httpx \
    python-pptx \
    python-docx \
    openpyxl \
    pillow \
    pyyaml \
    requests

# Set working directory
WORKDIR /workspace

# Create output directory and workspace structure
RUN mkdir -p /workspace/output /workspace/.claude/skills && \
    chown -R sandbox:sandbox /workspace

# Switch to non-root user
USER sandbox

# Default command to keep container running
CMD ["tail", "-f", "/dev/null"]

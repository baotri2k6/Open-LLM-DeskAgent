FROM python:3.10-slim

# Prevent interactive prompts during installs
ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js, git, build tools, and system libraries for chromium/sqlite
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libsqlite3-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy dependencies definitions
COPY requirements.txt package.json ./

# Install python and npm dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && npm install --omit=dev

# Copy the rest of the application
COPY . .

# Expose ports for Python Server (8765) and Websocket/OBS stream (9001)
EXPOSE 8765 9001

# Run the python backend server
CMD ["python", "backend/server.py"]

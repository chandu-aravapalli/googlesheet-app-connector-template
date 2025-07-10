FROM python:3.10-slim-buster
ARG ENVIRONMENT

WORKDIR /usr/src/app

# Set environment variables to prevent PyO3 conflicts
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
ENV CRYPTOGRAPHY_USE_PURE_PYTHON=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for cryptography and Google API libraries
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        git \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Upgrade to latest pip
RUN pip install --upgrade pip

# Install workflows-cdk package
RUN pip install git+https://github.com/stacksyncdata/workflows-cdk.git@prod

# Install dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the scripts
COPY . .

# Make the entrypoint executable
RUN chmod +x ./config/entrypoint.sh

# Expose port
EXPOSE 8080

# Run the entrypoint to start the Gunicorn production server
ENTRYPOINT ["sh", "./config/entrypoint.sh"]

# RUN in interactive mode
# UNIX: docker run --rm -p 2001:8080 -it -e ENVIRONMENT=dev -e REGION=besg -v $PWD:/usr/src/app/ workflows-app-example
# Windows: docker run --rm -p 2001:8080 -it -e ENVIRONMENT=dev -e REGION=besg -v ${PWD}:/usr/src/app/ workflows-app-example

# BUILD container
# docker build -t workflows-app-example . --build-arg ENVIRONMENT=dev
# docker build --no-cache -t workflows-app-example . --build-arg ENVIRONMENT=dev

# CONNECT to container terminal
# docker exec -it workflows-app-example bash

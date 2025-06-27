# Run ``make docker-dev`` from the root of the project


# Define an argument for the Python version, defaulting to 3.12 if not provided.
ARG PYTHON_VERSION=3.12.4
FROM python:${PYTHON_VERSION}-slim
LABEL authors="parking-system"

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# output is written directly to stdout or stderr without delay, making logs appear immediately in the console or in log files.
ENV PYTHONUNBUFFERED=1

# keep this in case some commands use sudo (tesseract for example). This docker doesn't need a password
#RUN apt-get update &&  apt-get install -y sudo && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt update -y
RUN apt upgrade -y
RUN apt-get install build-essential -y
RUN apt-get install curl -y
RUN apt autoremove -y
RUN apt autoclean -y

# Set environment variables
ENV APP_DIR=/parking-management-system
# Set working directory
WORKDIR $APP_DIR

# copy dependencies and installing them before copying the project to not rebuild the .env every time
COPY pyproject.toml uv.lock Makefile $APP_DIR

RUN make install-prod

COPY . $APP_DIR

# Create database directory
RUN mkdir -p /data

# Expose ports
EXPOSE 8501 8080

# Default command to run both services
CMD ["make", "run-app"]

FROM python:3.12.7

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire application first
COPY . .

# Install poetry
RUN pip install poetry

# Configure poetry to create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "uvicorn", "visualization.backend.main:app", "--host", "0.0.0.0", "--port", "8000"] 

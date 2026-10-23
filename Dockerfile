# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Create a non-root user that Hugging Face expects (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory in the container
WORKDIR $HOME/app

# Become root temporarily to install system dependencies
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY --chown=user requirements.txt .

# Switch back to user
USER user
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the BERT model so it doesn't download on every startup
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the current directory contents into the container
COPY --chown=user . $HOME/app

# Define environment variable
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Initialize DB and start gunicorn at runtime
CMD bash -c "python init_db.py && gunicorn -b 0.0.0.0:7860 run:app --timeout 120 --workers 2"

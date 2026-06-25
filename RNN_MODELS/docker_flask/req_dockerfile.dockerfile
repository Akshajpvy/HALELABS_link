# Dockerfile
FROM tensorflow/tensorflow:2.12.0

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY water_quality_vertex_ai.py /app/
WORKDIR /app

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    flask \
    gunicorn \
    google-cloud-storage \
    google-cloud-firestore \
    google-cloud-pubsub \
    pandas \
    scikit-learn

# Run the application
CMD exec gunicorn --bind :8080 --workers 4 --threads 8 --timeout 0 water_quality_vertex_ai:app
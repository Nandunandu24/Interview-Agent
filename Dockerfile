# Use a lightweight python image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose Streamlit default port and FastAPI port
EXPOSE 8501
EXPOSE 8000

# Make the start script executable and fix line endings
RUN sed -i -e 's/\r$//' start.sh && chmod +x start.sh

# Run the start script
CMD ["./start.sh"]

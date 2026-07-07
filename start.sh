#!/bin/bash

# Start FastAPI backend in the background on port 8000
echo "Starting FastAPI backend server..."
python server.py &

# Wait for backend to spin up
sleep 3

# Start Streamlit frontend on the port specified by Railway (defaulting to 8501)
PORT=${PORT:-8501}
echo "Starting Streamlit frontend on port $PORT..."
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

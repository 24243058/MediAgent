FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

# Default: run the FastAPI backend.
# For the Streamlit frontends, override the command, e.g.:
#   docker run <image> streamlit run frontend/patient_portal.py --server.port 8501
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY ml/ ml/
COPY data/Occupancy_Estimation.csv data/Occupancy_Estimation.csv
COPY backend/ backend/
COPY twin/ twin/

# Train the model inside the image so it matches the library versions in the container
RUN python ml/save_model.py

ENV DATABASE_URL=sqlite:////data/twin.db
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
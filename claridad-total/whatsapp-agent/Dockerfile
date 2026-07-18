FROM python:3.12-slim

WORKDIR /app

# Dependencias primero (mejor cache de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la app
COPY . .

# Datos mutables (conversaciones/leads/visitas) en un volumen persistente
ENV DATA_DIR=/data
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

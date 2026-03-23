FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8081

ENV PORT=8081
ENV SERVICE_NAME=tns-app
ENV AUTO_GENERATE=true

CMD ["python", "app.py"]

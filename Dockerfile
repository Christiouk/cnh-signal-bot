FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

# Expose the HTTP trigger port so Railway routes public traffic here
EXPOSE 8080

CMD ["python", "main.py", "--schedule"]

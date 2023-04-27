FROM python:3.9.2-slim

WORKDIR /app
ENTRYPOINT ["python3", "main.py"]

COPY requirements.txt .
RUN pip3 install --no-cache -r ./requirements.txt

RUN mkdir commands
COPY main.py .
COPY database.py .
COPY commands/* ./commands

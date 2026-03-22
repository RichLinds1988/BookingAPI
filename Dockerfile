FROM python:3.12-slim

WORKDIR /project

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FLASK_APP points to boot.py at root which adds src/ to the path itself
ENV FLASK_APP=boot.py

EXPOSE 5000

CMD ["bash", "-c", "flask db upgrade && python run.py"]

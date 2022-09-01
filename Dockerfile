FROM python:3.10.5

COPY "requirements.txt" "/tmp/qndos_requirements.txt"
RUN pip install -r /tmp/qndos_requirements.txt

# The application directory must be mounted as a volume on /app
WORKDIR /app

ENTRYPOINT ["python", "main.py"]

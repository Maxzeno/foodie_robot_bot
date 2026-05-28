FROM python:3.11.4-slim-bullseye
WORKDIR /app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev

# Copy requirements file and install dependencies
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Run pre_run.sh script (will remove this because might run on every docker run)
RUN chmod +x /app/pre_run.sh
ENTRYPOINT ["/app/pre_run.sh"]

# Default command to run the Django application
CMD ["gunicorn", "ctt.wsgi", "-b", "0.0.0.0:8000"]

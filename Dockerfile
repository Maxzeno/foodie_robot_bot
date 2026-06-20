FROM python:3.11.4-slim-bullseye
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install GDAL + PostgreSQL headers (needed by psycopg2) + cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Optional: let pip know where to find GDAL headers
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy and install Python dependencies
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . /app

# Make sure your pre_run script is executable
RUN chmod +x /app/pre_run.sh

# Set the entrypoint and default command
ENTRYPOINT ["/app/pre_run.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "foodie_robot.asgi:application"]

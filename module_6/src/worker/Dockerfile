FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the entire worker build context into /app
# This must include:
# - consumer.py
# - etl/
# - ../db/load_data.py and ../data/applicant_data.json via the build context layout below
COPY . /app

USER 1000

# Default command (compose can override)
CMD ["python", "consumer.py"]
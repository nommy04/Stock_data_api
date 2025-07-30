FROM python:3.12-slim

# Install cron and dependencies
RUN apt-get update && apt-get install -y cron

# Create app directory
WORKDIR /app

# Copy the script and requirements
COPY data_ingestion.py ./
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the crontab file to /etc/cron.d/ with correct permissions
COPY cron/crontab.txt /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob

# Create a log file to monitor cron job output
RUN touch /var/log/cron.log

# Run cron in foreground (Docker requirement)
CMD ["cron", "-f"]

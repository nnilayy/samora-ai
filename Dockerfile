FROM dailyco/pipecat-base:latest-py3.11

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the backend code (bot.py last to bust cache on code changes)
COPY backend/prompts/ ./prompts/
COPY backend/db_functions/ ./db_functions/
COPY backend/db.py .
COPY backend/bot.py .

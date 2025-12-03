FROM dailyco/pipecat-base:latest-py3.11

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install daily-python separately (so we don't invalidate requirements cache)
RUN pip install daily-python==0.22.0

# Copy the bot code
COPY agent.py .

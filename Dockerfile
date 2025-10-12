# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for headless Chrome and weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencies for adding Chrome repo and for weasyprint
    wget \
    gnupg \
    ca-certificates \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install Chrome using the recommended method
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Make port 8051 available to the world outside this container
EXPOSE 8051

# Define environment variable
ENV NAME World

# Run app_main.py when the container launches
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8051", "app_main:server"]
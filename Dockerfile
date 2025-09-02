# Stage 1: Build stage (only used if compiling dependencies)
FROM python:3.9-slim as build-stage

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final stage
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the contents from the build stage (dependencies only)
COPY --from=build-stage /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=build-stage /usr/local/bin /usr/local/bin

# Add non-root user and switch to it for better security
RUN useradd -m flaskuser

# Copy application code
COPY . /app

# Change ownership of /app to flaskuser after user is created
RUN chown -R flaskuser:flaskuser /app

# Remove pip cache and unnecessary files (optional)
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Switch to the non-root user
USER flaskuser

# Expose the port your Flask app will run on
EXPOSE 7860

# Run the Flask app using gunicorn with an infinite request timeout
# CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "0", "app:app"]
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "0", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

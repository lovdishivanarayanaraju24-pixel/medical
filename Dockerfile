FROM python:3.10-slim

# Install system dependencies for OCR and building python packages
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000 for Hugging Face
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=$HOME/app

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy the current directory contents into the container at $HOME/app setting the owner to the user
COPY --chown=user . $HOME/app

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements_hf.txt

# Create uploads directory with appropriate permissions
RUN mkdir -p $HOME/app/uploads && chmod 777 $HOME/app/uploads

# Build the frontend static files if there is a build step, otherwise we just serve existing files
# We'll assume the frontend/dist or frontend/static is already pushed to git and copied.

# Expose port 7860 which is required for Hugging Face Spaces
EXPOSE 7860

# Run the FastAPI application on port 7860
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860"]

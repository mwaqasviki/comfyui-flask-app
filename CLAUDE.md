# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based API wrapper for ComfyUI workflows, enabling programmatic access to various AI image and video generation models including FLUX, OmniGen, and CogVideoX.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask development server
python app.py
# Server runs on http://0.0.0.0:7860
```

### Production Deployment (Docker)
```bash
# Build Docker image
docker build -t comfyui-flask-app .

# Run with Gunicorn (production)
docker run -p 7860:7860 comfyui-flask-app
```

## Architecture

### Core Components

1. **app.py** - Main Flask application with the following API endpoints:
   - `/generate_image` - Text-to-image generation using FLUX1.DEV
   - `/omnigen/image_to_image` - Image editing with text prompts using OmniGen
   - `/v1/image_to_video` - Image-to-video generation using CogVideoX-5B-12V (async)
   - `/v1/text_to_video` - Text-to-video generation using CogVideoX-5B (async)
   - `/v1/video_tasks/<prompt_id>` - Check video generation status and retrieve results

2. **WebSocket Integration** - Communicates with ComfyUI backend server via WebSocket for real-time workflow execution monitoring

3. **Workflow Templates** - Pre-configured ComfyUI workflows in `/workflows/` directory:
   - Each workflow is a JSON file defining the ComfyUI node graph
   - Workflows are loaded and modified dynamically based on API inputs

### Key Implementation Details

- **Authentication**: Bearer token required in Authorization header for all API calls
- **Image Handling**: Supports both file uploads and base64-encoded images
- **Async Video Generation**: Video generation endpoints return a prompt_id for status checking
- **Static File Serving**: Generated images/videos temporarily stored in `/static/` directory

### Environment Configuration

Required environment variables (loaded from .env):
- `SERVER_ADDRESS` - ComfyUI backend server URL
- `WS_ADDRESS` - WebSocket endpoint for ComfyUI

### API Response Patterns

- Image generation returns base64-encoded images in JSON
- Video generation returns prompt_id with 202 status, then video file on completion
- All endpoints include proper error handling with descriptive messages
# ComfyUI Flask API

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0.2-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A powerful Flask-based REST API wrapper for ComfyUI, providing easy programmatic access to state-of-the-art AI models for image and video generation.

## 🌟 Features

- **🎨 Text-to-Image Generation** - Create stunning images from text prompts using FLUX1.DEV
- **🖼️ Image-to-Image Transformation** - Edit and transform images with text prompts using OmniGen
- **🎬 Image-to-Video Generation** - Convert static images to dynamic videos with CogVideoX
- **📹 Text-to-Video Generation** - Generate videos directly from text descriptions
- **⚡ Real-time Processing** - WebSocket integration for live workflow execution monitoring
- **🔐 Secure Authentication** - Bearer token authentication for all API endpoints
- **🐳 Docker Support** - Easy deployment with Docker containerization
- **📊 Async Processing** - Non-blocking video generation with status tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- ComfyUI backend server running
- Required environment variables configured

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/comfyui-flask-app.git
cd comfyui-flask-app
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file in the project root:
```env
SERVER_ADDRESS=http://your-comfyui-server:8188
WS_ADDRESS=ws://your-comfyui-server:8188/ws
```

4. **Run the application**
```bash
python app.py
```

The API will be available at `http://localhost:7860`

## 🐳 Docker Deployment

### Build and run with Docker

```bash
# Build the Docker image
docker build -t comfyui-flask-api .

# Run the container
docker run -p 7860:7860 --env-file .env comfyui-flask-api
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  comfyui-api:
    build: .
    ports:
      - "7860:7860"
    env_file:
      - .env
    restart: unless-stopped
```

## 📡 API Endpoints

### 1. Generate Image from Text

**POST** `/generate_image`

Generate high-quality images from text prompts using FLUX1.DEV model.

```bash
curl -X POST http://localhost:7860/generate_image \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_prompt": "A futuristic city with flying cars at sunset"
  }'
```

**Response:**
```json
{
  "images": ["base64_encoded_image_data..."]
}
```

### 2. Transform Image with Text (OmniGen)

**POST** `/omnigen/image_to_image`

Edit images using natural language instructions.

```bash
curl -X POST http://localhost:7860/omnigen/image_to_image \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_prompt": "make the sky purple and add northern lights",
    "image_url": "https://example.com/image.jpg",
    "steps": 50
  }'
```

### 3. Generate Video from Image

**POST** `/v1/image_to_video`

Convert static images to videos with motion prompts.

```bash
curl -X POST http://localhost:7860/v1/image_to_video \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_prompt": "camera slowly zooms in while leaves gently sway",
    "base64_image": "data:image/jpeg;base64,/9j/4AAQ...",
    "frame_rate": 24,
    "steps": 50
  }'
```

**Response:**
```json
{
  "prompt_id": "e5aa6918-bb2c-4fde-81d2-c759d64a3c57",
  "message": "Prompt queued successfully",
  "get_video_url": "https://your-domain.com/v1/video_tasks/e5aa6918-bb2c-4fde-81d2-c759d64a3c57"
}
```

### 4. Generate Video from Text

**POST** `/v1/text_to_video`

Create videos directly from text descriptions.

```bash
curl -X POST http://localhost:7860/v1/text_to_video \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_prompt": "A cat playing with a ball of yarn in slow motion",
    "frame_rate": 24,
    "steps": 50
  }'
```

### 5. Check Video Generation Status

**GET** `/v1/video_tasks/{prompt_id}`

Monitor video generation progress and download completed videos.

```bash
curl -X GET http://localhost:7860/v1/video_tasks/e5aa6918-bb2c-4fde-81d2-c759d64a3c57 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🛠️ Configuration

### Supported Image Formats
- JPEG/JPG
- PNG
- WebP

### Video Generation Options
- **Frame Rates**: 8, 12, or 24 fps
- **Steps**: Default 50 (higher = better quality, slower generation)
- **Format**: MP4

### Request Formats

All endpoints support multiple input formats:
- **File Upload**: Multipart form data
- **Base64 Image**: Embedded in JSON request
- **Image URL**: Direct URL reference

## 📂 Project Structure

```
comfyui-flask-app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── .env                  # Environment variables
├── workflows/            # ComfyUI workflow templates
│   ├── flux1_dev_checkpoint_workflow_api.json
│   ├── omnigen_image_to_image_workflow_api.json
│   ├── cogvideox_image_to_video_workflow_api.json
│   └── cogvideox_text_to_video_workflow_api.json
├── static/               # Generated images/videos
├── templates/            # HTML templates
└── images/               # Sample images

```

## 🔧 Advanced Usage

### Custom Workflows

You can add custom ComfyUI workflows by:

1. Export your workflow from ComfyUI as API format JSON
2. Place it in the `workflows/` directory
3. Create a new endpoint in `app.py` following the existing patterns

### Scaling Considerations

- Use a reverse proxy (nginx) for production deployments
- Implement caching for frequently requested content
- Consider using a queue system (Redis/RabbitMQ) for high-volume requests
- Store generated content in cloud storage (S3) instead of local filesystem

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - The powerful backend this API wraps
- [FLUX](https://github.com/black-forest-labs/flux) - State-of-the-art image generation
- [CogVideoX](https://github.com/THUDM/CogVideo) - Advanced video generation models
- [OmniGen](https://github.com/VectorSpaceLab/OmniGen) - Versatile image transformation

---

<p align="center">Made with ❤️ by M Waqas Viki, for developers</p>

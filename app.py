import os
import io
import json
import base64
import random
import urllib.request
import urllib.parse
import websocket
import uuid
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from PIL import Image
from werkzeug.utils import secure_filename
import urllib.parse
import urllib.request
import time

# Load environment variables from the .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}  # Define supported image types

# Set server and websocket addresses from environment variables
server_address = os.getenv("SERVER_ADDRESS")
ws_address = os.getenv("WS_ADDRESS")

# Generate a unique client ID
client_id = str(uuid.uuid4())

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_base64_image(b64_string):
    """Decode a base64 string and save it as an image in the static folder."""
    try:
        # Handle Data URI scheme if present
        if ',' in b64_string:
            header, encoded = b64_string.split(',', 1)
            ext = header.split('/')[1].split(';')[0] if '/' in header else 'png'
        else:
            encoded = b64_string
            ext = 'png'

        # Decode the image data
        image_data = base64.b64decode(encoded)

        # Generate a unique path for the image in the static folder
        image_path = f"static/{uuid.uuid4()}.{ext}"

        # Ensure directory exists
        os.makedirs('static', exist_ok=True)

        # Save the image
        with open(image_path, 'wb') as f:
            f.write(image_data)

        print(f"Image saved at: {image_path}", flush=True)

        # Return the path and URL of the saved image
        image_url = f"https://gosign-de-comfyui-api.hf.space/{image_path}"

        print(f"Image path (local): {image_path}", flush=True)
        print(f"Image URL (public): {image_url}", flush=True)

        return image_path, image_url

    except Exception as e:
        raise ValueError(f"Failed to save image: {e}")

def get_image(filename, subfolder, image_type, token):
    url_values = {'filename': filename, 'subfolder': subfolder, 'type': image_type}
    url = f"{server_address}/view?{urllib.parse.urlencode(url_values)}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        return urllib.request.urlopen(req).read()
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read())
        raise

def get_images(ws, workflow, token):
    prompt_id = queue_prompt(workflow, token)
    output_images = {}

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done

    history = get_history(prompt_id, token)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'], token)
                images_output.append(image_data)
        output_images[node_id] = images_output

    return output_images

# Default route for home welcome
@app.route('/')
def home():
    return render_template('home.html')

                ################################################
                # Generate text to image using FLUX1.DEV Model #
                ################################################

# Generate image route
@app.route('/generate_image', methods=['POST'])
def generate_image():
    data = request.json

    # Extract the token from the request headers
    token = request.headers.get('Authorization')

    if token is None:
        return jsonify({'error': 'No token provided'}), 400
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    # Base64 decode the encoded token
    # token = base64.b64decode(token).decode("utf-8")

    if 'text_prompt' not in data:
        return jsonify({'error': 'No text prompt provided'}), 400

    text_prompt = data['text_prompt']

    # Get the path to the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'workflows/flux1_dev_checkpoint_workflow_api.json')

    with open(file_path, 'r', encoding='utf-8') as file:
        workflow_jsondata = file.read()

    workflow = json.loads(workflow_jsondata)
    workflow["6"]["inputs"]["text"] = text_prompt

    # Generate a random 15-digit seed as an integer
    seednum = random.randint(100000000000000, 999999999999999)
    workflow["31"]["inputs"]["seed"] = seednum

    ws = websocket.WebSocket()

    try:
        ws.connect(f"{ws_address}?clientId={client_id}&token={token}", header=
        {"Authorization": f"Bearer {token}"})
    except websocket.WebSocketException as e:
        return jsonify({'error': f'WebSocket connection failed: {str(e)}'}), 500

    images = get_images(ws, workflow, token)
    ws.close()

    output_images_base64 = []

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            output_images_base64.append(img_str)

    return jsonify({'images': output_images_base64})


                ###################################################
                # Edit image with text prompt using OmniGen Model #
                ###################################################

# Route: OmniGen image to image
@app.route('/omnigen/image_to_image', methods=['POST'])
def omnigen_image_to_image():
    data = request.json

    # Extract and validate token
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({'error': 'Valid Bearer token required'}), 400
    token = token.split(" ")[1]

    # Validate text prompt
    text_prompt = data.get('text_prompt')
    if not text_prompt or not text_prompt.strip():
        return jsonify({'error': 'Text prompt is required'}), 400

    steps = data.get('steps')
    if not steps:
        steps = 50

    image_url = data.get('image_url')
    if not image_url:
        return jsonify({'error': 'image_url is required'}), 400

    # Handle uploaded image or base64 image
    image_file = request.files.get('image')
    base64_image = data.get('base64_image')

    image_path = None  # Initialize image path

    try:
        if image_file:
            # Check if the file has an allowed extension
            if not allowed_file(image_file.filename):
                return jsonify({'error': 'Unsupported image format'}), 400

            # Secure the filename
            filename = secure_filename(image_file.filename)

            # Generate a unique path for the image
            unique_filename = f"{uuid.uuid4()}_{filename}"
            image_path = os.path.join('static', unique_filename)

            # Ensure the 'static' directory exists
            os.makedirs('static', exist_ok=True)

            # Save the image to the static directory
            image_file.save(image_path)

            # Construct the public URL to access the image
            image_url = f"https://gosign-de-comfyui-api.hf.space/{image_path}"

        elif base64_image:
            # Save base64 image
            try:
                pass
                # image_path, image_url = save_base64_image(base64_image)
                # image_url = "https://drive.google.com/uc?id=1JEHEy0zCVWOob4421hLQIPMbO_ebeCPS&export=download"
            except Exception as e:
                raise ValueError(f'Invalid base64 image data: {str(e)}')

        else:
            return jsonify({'error': 'Image is required (file or base64)'}), 400

        # Load workflow configuration
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_path = os.path.join(current_dir, 'workflows/omnigen_image_to_image_workflow_api.json')
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Modify workflow with inputs
        workflow["6"]["inputs"]["prompt"] = "in image_1 " + text_prompt
        workflow["6"]["inputs"]["num_inference_steps"] = steps
        workflow["12"]["inputs"]["url"] = image_url

        # WebSocket connection to queue the prompt
        ws = websocket.WebSocket()
        ws.connect(f"{ws_address}?clientId={client_id}&token={token}",
                   header={"Authorization": f"Bearer {token}"})

        images = get_images(ws, workflow, token)
        ws.close()

        output_images_base64 = []

        for node_id in images:
            for image_data in images[node_id]:
                image = Image.open(io.BytesIO(image_data))
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                output_images_base64.append(img_str)

        return jsonify({'images': output_images_base64}), 200

    except Exception as e:
        return jsonify({'message': 'Unable to connect to the server. Make sure the server is running', 'error': str(e)}), 500

    finally:
        pass
        # Always delete the image if it was saved
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            print(f"Deleted temporary image: {image_path}", flush=True)


# Get image route
@app.route('/get_image/<filename>', methods=['GET'])
def get_image_file(filename):
    return send_file(filename, mimetype='image/png')


# Route to serve images
@app.route('/static/<path:filename>', methods=['GET'])
def serve_static(filename):
    print(f"Request for static file: {filename}", flush=True)
    return send_from_directory('static', filename)

# Make a request route
def make_request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode()  # Decode the response
            # print(response_body)
            return json.loads(response_body)  # Convert to JSON if valid
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code}, {e.reason}")
        print(e.read().decode())  # Print detailed error response
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")

# Helper: Queue the prompt
def queue_prompt(workflow, token):
    payload = {"prompt": workflow, "client_id": client_id}
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    response = make_request(f"{server_address}/prompt", data=json.dumps(payload).encode('utf-8'), headers=headers)
    if not response or 'prompt_id' not in response:
        raise ValueError("Failed to queue the prompt. Check the request or API response.")
    return response['prompt_id']

# Get ComfyUI prompt history
def get_history(prompt_id, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    return make_request(f"{server_address}/history/{prompt_id}", headers=headers)

def get_video_data(filename, subfolder, token):
    """
    Retrieve a video from the server using filename, subfolder, and token.
    """
    # Handle empty subfolder case gracefully
    subfolder = subfolder or ''  # Default to empty string if None

     # Construct query parameters
    url_values = {
        'filename': filename
    }

    # Build the URL with encoded query parameters
    url = f"{server_address}/view?{urllib.parse.urlencode(url_values)}"

    print(f"Requesting URL: {url}", flush=True)

    # Prepare the request with authorization token
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        # Fetch and return the video data
        response = urllib.request.urlopen(req)
        return response.read()

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode())  # Decode error message for readability
        raise

    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        raise

                ########################################################
                # Generate image to video using CogVideoX-5B-12V Model #
                ########################################################

# Route: Image to Video
@app.route('/v1/image_to_video', methods=['POST'])
def v1_image_to_video():
    data = request.json

    # Extract and validate token
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({'error': 'Valid Bearer token required'}), 400
    token = token.split(" ")[1]

    # Validate text prompt
    text_prompt = data.get('text_prompt')
    frame_rate = data.get('frame_rate')
    steps = data.get('steps')
    if not text_prompt or not text_prompt.strip():
        return jsonify({'error': 'Text prompt is required'}), 400

    # Check if frame_rate is missing or invalid
    if not frame_rate:  # If frame_rate is None, empty, or 0
        frame_rate = 24  # Default to 24 fps
    else:
        try:
            frame_rate = int(frame_rate)
            if frame_rate not in [8, 12, 24]:  # Ensure it's one of the allowed values
                return jsonify({'error': 'Frame rate must be a valid number (8, 12, or 24).'}), 400
        except ValueError:
            return jsonify({'error': 'Frame rate must be a valid number (8, 12, or 24).'}), 400

    if not steps:
        steps = 50
    # Handle uploaded image or base64 image
    image_file = request.files.get('image')
    base64_image = data.get('base64_image')

    image_path = None  # Initialize image path

    try:
        if image_file:
            # Check if the file has an allowed extension
            if not allowed_file(image_file.filename):
                return jsonify({'error': 'Unsupported image format'}), 400

            # Secure the filename
            filename = secure_filename(image_file.filename)

            # Generate a unique path for the image
            unique_filename = f"{uuid.uuid4()}_{filename}"
            image_path = os.path.join('static', unique_filename)

            # Ensure the 'static' directory exists
            os.makedirs('static', exist_ok=True)

            # Save the image to the static directory
            image_file.save(image_path)

            # Construct the public URL to access the image
            image_url = f"https://gosign-de-comfyui-api.hf.space/{image_path}"

        elif base64_image:
            # Save base64 image
            try:
                image_path, image_url = save_base64_image(base64_image)
            except Exception as e:
                raise ValueError(f'Invalid base64 image data: {str(e)}')

        else:
            return jsonify({'error': 'Image is required (file or base64)'}), 400

        # Load workflow configuration
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_path = os.path.join(current_dir, 'workflows/cogvideox_image_to_video_workflow_api.json')
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Modify workflow with inputs
        workflow["30"]["inputs"]["prompt"] = text_prompt
        workflow["31"]["inputs"]["prompt"] = "Low quality, watermark, strange motion, blur"
        workflow["44"]["inputs"]["frame_rate"] = frame_rate
        workflow["57"]["inputs"]["steps"] = steps
        workflow["73"]["inputs"]["url"] = image_url

        # WebSocket connection to queue the prompt
        ws = websocket.WebSocket()
        ws.connect(f"{ws_address}?clientId={client_id}&token={token}",
                   header={"Authorization": f"Bearer {token}"})

        # Queue the prompt
        prompt_id = queue_prompt(workflow, token)

        return jsonify({'prompt_id': prompt_id, 'message': 'Prompt queued successfully', 'get_video_url': f'https://gosign-de-comfyui-api.hf.space/v1/video_tasks/{prompt_id}'}), 202

    except Exception as e:
        return jsonify({'message': 'Unbale to connect to the server. Make sure the server is running', 'error': str(e)}), 500

    finally:
        pass
        # Always delete the image if it was saved
        # if image_path and os.path.exists(image_path):
        #     os.remove(image_path)
        #     print(f"Deleted temporary image: {image_path}", flush=True)


                ###################################################
                # Generate text to video using CogVideoX-5B Model #
                ###################################################

# Route: Text to Video
@app.route('/v1/text_to_video', methods=['POST'])
def v1_text_to_video():
    data = request.json

    # Extract and validate token
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({'error': 'Valid Bearer token required'}), 400
    token = token.split(" ")[1]

    # Validate text prompt
    text_prompt = data.get('text_prompt')
    frame_rate = data.get('frame_rate')
    steps = data.get('steps')
    if not text_prompt or not text_prompt.strip():
        return jsonify({'error': 'Text prompt is required'}), 400

    # Check if frame_rate is missing or invalid
    if not frame_rate:  # If frame_rate is None, empty, or 0
        frame_rate = 24  # Default to 24 fps
    else:
        try:
            frame_rate = int(frame_rate)
            if frame_rate not in [8, 12, 24]:  # Ensure it's one of the allowed values
                return jsonify({'error': 'Frame rate must be a valid number (8, 12, or 24).'}), 400
        except ValueError:
            return jsonify({'error': 'Frame rate must be a valid number (8, 12, or 24).'}), 400

    if not steps:
        steps = 50

    try:
        # Load workflow configuration
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_path = os.path.join(current_dir, 'workflows/cogvideox_text_to_video_workflow_api.json')
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Modify workflow with inputs
        workflow["30"]["inputs"]["prompt"] = text_prompt
        workflow["31"]["inputs"]["prompt"] = "Low quality, watermark, strange motion, blur"
        workflow["33"]["inputs"]["frame_rate"] = frame_rate
        workflow["34"]["inputs"]["steps"] = steps

        # WebSocket connection to queue the prompt
        ws = websocket.WebSocket()
        ws.connect(f"{ws_address}?clientId={client_id}&token={token}",
                   header={"Authorization": f"Bearer {token}"})

        # Queue the prompt
        prompt_id = queue_prompt(workflow, token)

        return jsonify({'prompt_id': prompt_id, 'message': 'Prompt queued successfully', 'get_video_url': f'https://gosign-de-comfyui-api.hf.space/v1/video_tasks/{prompt_id}'}), 202

    except Exception as e:
        return jsonify({'message': 'Unbale to connect to the server. Make sure the server is running', 'error': str(e)}), 500


# Get video_tasks route
@app.route('/v1/video_tasks/<prompt_id>', methods=['GET'])
def video_tasks(prompt_id):
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({'error': 'Valid Bearer token required'}), 400
    token = token.split(" ")[1]

    try:

        # Establish WebSocket connection to fetch real-time status
        ws = websocket.WebSocket()
        ws.connect(f"{ws_address}?clientId={client_id}&token={token}",
                   header={"Authorization": f"Bearer {token}"})

        # Request current status of the specific prompt
        ws.send(json.dumps({"type": "get_status", "prompt_id": prompt_id}))
        response = json.loads(ws.recv())

        # Extract the necessary fields for the specific prompt
        queue_remaining = response.get('data', {}).get('status', {}).get('exec_info', {}).get('queue_remaining', 0)

        # Now proceed to check if the prompt has completed successfully
        history = get_history(prompt_id, token).get(prompt_id, {})

        if not history:
            return jsonify({
                'message': 'Video is being generated.',
                'status': 'pending',
                'prompts_in_queue': queue_remaining
            }), 202

        video_data = None

        # Extract video or GIF details
        for node_id, node_output in history.get('outputs', {}).items():
            if 'gifs' in node_output:
                video = node_output['gifs'][0]  # Take the first available GIF/video

                try:
                    video_data = get_video_data(video['filename'], video['subfolder'], token)
                    break  # Stop after fetching the first valid video
                except Exception as e:
                    print(f"Failed to retrieve video: {str(e)}")

        if not video_data:
            return jsonify({'error': 'Failed to retrieve video data.'}), 500

        # Save the video locally
        # local_video_path = f"static/generated_image_to_video_{prompt_id}.mp4"
        # with open(local_video_path, 'wb') as f:
        #     f.write(video_data)

        # Send the video as an HTTP response
        return send_file(
            io.BytesIO(video_data),
            mimetype='video/mp4',
            as_attachment=True,
            download_name='generated_video.mp4'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route: Image to Video old
@app.route('/image_to_video', methods=['POST'])
def image_to_video():
    data = request.json

    # Extract and validate token
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({'error': 'Valid Bearer token required'}), 400
    token = token.split(" ")[1]

    # Validate text prompt
    text_prompt = data.get('text_prompt')
    frame_rate = data.get('frame_rate')
    steps = data.get('steps')
    if not text_prompt or not text_prompt.strip():
        return jsonify({'error': 'Text prompt is required'}), 400

    # Check if frame_rate is missing or invalid
    if not frame_rate:  # If frame_rate is None, empty, or 0
        frame_rate = 24  # Default to 24 fps
    else:
        try:
            frame_rate = int(frame_rate)
            if frame_rate not in [8, 12, 24]:
                return jsonify({'error': 'Frame rate must be a valid number (8, 12, or 24).'}), 400
        except ValueError:
            return jsonify({'error': 'Frame rate must be a valid number (8, 12, or 24).'}), 400

    if not steps:
        steps = 50

    # Handle uploaded image or base64 image
    image_file = request.files.get('image')
    base64_image = data.get('base64_image')

    image_path = None  # Initialize image path

    try:
        if image_file:
            # Check if the file has an allowed extension
            if not allowed_file(image_file.filename):
                return jsonify({'error': 'Unsupported image format'}), 400

            # Secure the filename
            filename = secure_filename(image_file.filename)

            # Generate a unique path for the image
            unique_filename = f"{uuid.uuid4()}_{filename}"
            image_path = os.path.join('static', unique_filename)

            # Ensure the 'static' directory exists
            os.makedirs('static', exist_ok=True)

            # Save the image to the static directory
            image_file.save(image_path)

            # Construct the public URL to access the image
            image_url = f"https://gosign-de-comfyui-api.hf.space/{image_path}"

        elif base64_image:
            # Save base64 image
            try:
                image_path, image_url = save_base64_image(base64_image)
            except Exception as e:
                raise ValueError(f'Invalid base64 image data: {str(e)}')

        else:
            return jsonify({'error': 'Image is required (file or base64)'}), 400

        # Load workflow configuration
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_path = os.path.join(current_dir, 'workflows/cogvideox_image_to_video_workflow_api.json')
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Modify workflow with inputs
        workflow["30"]["inputs"]["prompt"] = text_prompt
        workflow["31"]["inputs"]["prompt"] = "Low quality, watermark, strange motion, blur"
        workflow["44"]["inputs"]["frame_rate"] = frame_rate
        workflow["57"]["inputs"]["steps"] = steps
        workflow["73"]["inputs"]["url"] = image_url

        # WebSocket connection to queue and monitor workflow
        ws = websocket.WebSocket()
        ws.connect(f"{ws_address}?clientId={client_id}&token={token}",
                   header={"Authorization": f"Bearer {token}"})

        # Queue the prompt and wait for completion
        prompt_id = queue_prompt(workflow, token)


        # Wait for workflow execution to complete
        last_ping = time.time()
        PING_INTERVAL = 30

        # Wait for workflow execution to complete
        while True:
            message = json.loads(ws.recv())
            if message.get('type') == 'executing' and message['data']['node'] is None \
                    and message['data']['prompt_id'] == prompt_id:
                break

            # Send a ping if PING_INTERVAL has passed
            if time.time() - last_ping > PING_INTERVAL:
                ws.send('ping')
                last_ping = time.time()

        # Fetch the history of the workflow
        history = get_history(prompt_id, token).get(prompt_id, {})
        video_data = None

        # Find the video or GIF data from the outputs
        for node_id, node_output in history.get('outputs', {}).items():
            if 'gifs' in node_output:
                video = node_output['gifs'][0]  # Take the first video/GIF
                try:
                    video_data = get_video_data(video['filename'], video['subfolder'], token)
                    break  # Stop after fetching the first valid video
                except Exception as e:
                    print(f"Failed to retrieve video: {str(e)}")

        # Ensure video data was retrieved
        if not video_data:
            raise ValueError('Failed to generate video')

        # Save the video locally
        local_video_path = f"static/generated_image_to_video_{prompt_id}.mp4"
        with open(local_video_path, 'wb') as f:
            f.write(video_data)

        # Construct the public URL for the video

        # video_url = f"https://gosign-de-comfyui-api.hf.space/{local_video_path}"

        # Prepare the response with the video URL
        # response_data = {
        #     'video_url': video_url,
        #     'message': 'Video generated successfully'
        # }

        # return jsonify(response_data), 200

        # Send the video as an HTTP response
        response = send_file(
            io.BytesIO(video_data),
            mimetype='video/mp4',
            as_attachment=True,
            download_name='generated_video.mp4'
        )

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Always delete the image if it was saved
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            print(f"Deleted temporary image: {image_path}", flush=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=True)

# server/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import subprocess

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Enable CORS
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create uploads directory if it doesn’t exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'wmv', 'mkv', 'mts'}

def convert_to_hls(input_path, output_base):
    # Define resolutions and their settings
    resolutions = [
        {"height": 144, "bitrate": "200k"},
        {"height": 240, "bitrate": "400k"},
        {"height": 360, "bitrate": "800k"},
        {"height": 480, "bitrate": "1200k"},
        {"height": 720, "bitrate": "2500k"},
        {"height": 1080, "bitrate": "5000k"},
        {"height": 1440, "bitrate": "8000k"}
    ]

    # Base FFmpeg command
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', input_path,
        '-preset', 'fast',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-f', 'hls',
        '-hls_time', '10',
        '-hls_list_size', '0',
        '-hls_segment_filename', f'{output_base}/v%v/segment%d.ts',
    ]

    # Add scaling and bitrate for each resolution
    for i, res in enumerate(resolutions):
        ffmpeg_cmd.extend([
            f'-vf:{i}', f'scale=-2:{res["height"]}',
            f'-b:v:{i}', res["bitrate"],
            f'-map', '0:v',
            f'-map', '0:a?',
        ])

    # Variable stream mapping
    var_stream_map = ' '.join(f'v:{i},a:{i}' for i in range(len(resolutions)))
    ffmpeg_cmd.extend([
        '-var_stream_map', var_stream_map,
        '-master_pl_name', f'{output_base}/master.m3u8',
        f'{output_base}/v%v/playlist.m3u8'
    ])

    # Wrap FFmpeg with cpulimit to limit CPU to 50%
    cmd = ['cpulimit', '--limit', '50', '--'] + ffmpeg_cmd

    try:
        # Run the command
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.info(f"HLS conversion completed for {input_path}")
        logger.debug(f"FFmpeg output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Create output directory for HLS files
    output_base = os.path.join(app.config['UPLOAD_FOLDER'], f"hls_{os.path.splitext(filename)[0]}")
    os.makedirs(output_base, exist_ok=True)

    try:
        # Convert to HLS with CPU limit
        convert_to_hls(file_path, output_base)
        return jsonify({
            'message': 'File uploaded and converted to HLS successfully',
            'filename': filename,
            'hls_master': f"hls_{os.path.splitext(filename)[0]}/master.m3u8"
        }), 200
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return jsonify({'error': 'HLS conversion failed'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
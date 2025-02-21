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

def write_master_m3u8(output_base, resolutions_completed):
    """Generate or update the master.m3u8 file with completed resolutions."""
    master_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
    for res in resolutions_completed:
        master_content += (
            f"#EXT-X-STREAM-INF:BANDWIDTH={res['bitrate'].replace('k', '000')},RESOLUTION={res['resolution']}\n"
            f"v{res['index']}/playlist.m3u8\n"
        )
    with open(f"{output_base}/master.m3u8", 'w') as f:
        f.write(master_content)
    logger.info(f"Updated master.m3u8 with resolutions: {[r['height'] for r in resolutions_completed]}")

def convert_resolution_to_hls(input_path, output_base, resolution):
    """Convert a single resolution to HLS segments and playlist."""
    index = resolution['index']
    height = resolution['height']
    bitrate = resolution['bitrate']
    output_dir = f"{output_base}/v{index}"
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        'cpulimit', '--limit', '50', '--',  # Limit CPU to 50%
        'ffmpeg',
        '-i', input_path,
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264',
        '-b:v', bitrate,
        '-c:a', 'aac',
        '-f', 'hls',
        '-hls_time', '10',
        '-hls_list_size', '0',
        '-hls_segment_filename', f'{output_dir}/segment%d.ts',
        f'{output_dir}/playlist.m3u8'
    ]

    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.info(f"Completed HLS conversion for {height}p")
        logger.debug(f"FFmpeg output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error for {height}p: {e.stderr}")
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

    # Define resolutions in order
    resolutions = [
        {"index": 0, "height": 144, "bitrate": "200k", "resolution": "256x144"},
        {"index": 1, "height": 240, "bitrate": "400k", "resolution": "426x240"},
        {"index": 2, "height": 360, "bitrate": "800k", "resolution": "640x360"},
        {"index": 3, "height": 480, "bitrate": "1200k", "resolution": "854x480"},
        {"index": 4, "height": 720, "bitrate": "2500k", "resolution": "1280x720"},
        {"index": 5, "height": 1080, "bitrate": "5000k", "resolution": "1920x1080"},
        {"index": 6, "height": 1440, "bitrate": "8000k", "resolution": "2560x1440"}
    ]

    try:
        # Process resolutions sequentially, starting with 144p
        completed_resolutions = []
        for res in resolutions:
            completed_resolutions.append(res)
            write_master_m3u8(output_base, completed_resolutions)
            convert_resolution_to_hls(file_path, output_base, res)

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
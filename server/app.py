# server/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import subprocess
from threading import Thread
import re

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

# Global dictionary to store FFmpeg progress per file
ffmpeg_progress = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'wmv', 'mkv', 'mts'}

def write_master_m3u8(output_base, resolutions_available):
    """Generate or update the master.m3u8 file with completed resolutions."""
    master_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
    for res in resolutions_available:
        master_content += (
            f"#EXT-X-STREAM-INF:BANDWIDTH={res['bitrate'].replace('k', '000')},RESOLUTION={res['resolution']}\n"
            f"v{res['index']}/playlist.m3u8\n"
        )
    with open(f"{output_base}/master.m3u8", 'w') as f:
        f.write(master_content)
    logger.info(f"Updated master.m3u8 with resolutions: {[r['height'] for r in resolutions_available]}")

def convert_resolution_to_hls(input_path, output_base, resolution, filename):
    """Convert a single resolution to HLS segments and playlist with progress updates."""
    index = resolution['index']
    height = resolution['height']
    bitrate = resolution['bitrate']
    output_dir = f"{output_base}/v{index}"
    os.makedirs(output_dir, exist_ok=True)

    # Calculate CPU limit dynamically: 50% of total CPU capacity
    num_cores = os.cpu_count()  # Equivalent to `nproc` in Python
    cpu_limit = (num_cores * 100) // 2  # Integer division for 50% of total capacity

    cmd = [
        'cpulimit', '--limit', str(cpu_limit), '--',  # Dynamic limit based on cores
        'ffmpeg',
        '-i', input_path,
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264',
        '-b:v', bitrate,
        '-c:a', 'aac',
        '-f', 'hls',
        '-hls_time', '2',  # Changed from 10 to 2 seconds
        '-hls_list_size', '0',
        '-hls_segment_filename', f'{output_dir}/segment%d.ts',
        f'{output_dir}/playlist.m3u8',
        '-progress', 'pipe:2'  # Output progress to stderr
    ]

    # Initialize progress for this file and resolution
    ffmpeg_progress[filename] = ffmpeg_progress.get(filename, {})
    ffmpeg_progress[filename][height] = {'status': 'processing', 'progress': {}}

    try:
        # Run FFmpeg with Popen to capture stderr in real-time
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        # Regular expression to parse FFmpeg progress (e.g., "frame=123", "time=00:01:23")
        progress_re = re.compile(r'(frame|fps|size|time|bitrate|speed)=(.+)')

        # Read FFmpeg output line-by-line
        for line in process.stderr:
            match = progress_re.search(line)
            if match:
                key, value = match.groups()
                ffmpeg_progress[filename][height]['progress'][key] = value
                logger.debug(f"FFmpeg progress for {filename} ({height}p): {key}={value}")

        # Wait for FFmpeg to finish and check exit code
        process.wait()
        if process.returncode != 0:
            error_output = process.stderr.read()
            logger.error(f"FFmpeg error for {height}p: {error_output}")
            ffmpeg_progress[filename][height]['status'] = 'error'
            raise subprocess.CalledProcessError(process.returncode, cmd, stderr=error_output)

        logger.info(f"Completed HLS conversion for {height}p")
        ffmpeg_progress[filename][height]['status'] = 'completed'

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed for {height}p: {e.stderr}")
        ffmpeg_progress[filename][height]['status'] = 'error'
        raise
    finally:
        # Clean up process if needed
        process.stderr.close()

def background_convert(file_path, output_base, resolutions, filename):
    """Run HLS conversion in the background, processing resolutions sequentially."""
    available_resolutions = []
    try:
        res = resolutions[0]
        available_resolutions.append(res)
        write_master_m3u8(output_base, available_resolutions)
        convert_resolution_to_hls(file_path, output_base, res, filename)
        for res in resolutions[1:]:
            convert_resolution_to_hls(file_path, output_base, res, filename)
            available_resolutions.append(res)
            write_master_m3u8(output_base, available_resolutions)
        logger.info(f"Background HLS conversion completed for {file_path}")
    except Exception as e:
        logger.error(f"Background conversion failed: {e}")

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

    # Start background conversion
    Thread(target=background_convert, args=(file_path, output_base, resolutions, filename)).start()

    # Return immediately with the HLS master URL
    return jsonify({
        'message': 'Upload started, HLS conversion in progress',
        'filename': filename,
        'hls_master': f"hls_{os.path.splitext(filename)[0]}/master.m3u8"
    }), 202

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    """Serve static HLS files from the uploads directory."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/status/<filename>')
def conversion_status(filename):
    """Check the status of HLS conversion for a given filename with FFmpeg progress."""
    output_base = os.path.join(app.config['UPLOAD_FOLDER'], f"hls_{os.path.splitext(filename)[0]}")
    master_path = f"{output_base}/master.m3u8"
    
    total_resolutions = 7  # Total number of resolutions (144p to 1440p)

    if not os.path.exists(master_path):
        # Check if the original file exists but conversion hasn’t started
        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            return jsonify({
                'status': 'pending',
                'resolutions_available': 0,
                'total_resolutions': total_resolutions,
                'ffmpeg_progress': ffmpeg_progress.get(filename, {})
            }), 200
        return jsonify({'status': 'not_found', 'error': 'File not uploaded'}), 404

    try:
        with open(master_path, 'r') as f:
            lines = f.readlines()
            resolutions_available = sum(1 for line in lines if 'playlist.m3u8' in line)
        
        status = 'completed' if resolutions_available == total_resolutions else 'processing'
        return jsonify({
            'status': status,
            'resolutions_available': resolutions_available,
            'total_resolutions': total_resolutions,
            'hls_master': f"hls_{os.path.splitext(filename)[0]}/master.m3u8",
            'ffmpeg_progress': ffmpeg_progress.get(filename, {})
        }), 200
    except Exception as e:
        logger.error(f"Error reading master.m3u8: {e}")
        return jsonify({'status': 'error', 'error': str(e), 'ffmpeg_progress': ffmpeg_progress.get(filename, {})}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
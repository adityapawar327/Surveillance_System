import boto3
import os
from dotenv import load_dotenv
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.config import Config
import threading
from functools import partial
import subprocess
import json
import tempfile
import shutil

# Load AWS credentials from .env
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_S3_REGION = os.getenv("AWS_S3_REGION")

# Optimized S3 configuration
s3_config = Config(
    region_name=AWS_S3_REGION,
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    max_pool_connections=50,  # Increase connection pool
    s3={
        'use_accelerate_endpoint': True,  # Enable S3 Transfer Acceleration if configured
        'addressing_style': 'virtual'
    }
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=s3_config
)

# Thread-local storage for S3 clients (for thread safety)
thread_local = threading.local()

def get_s3_client():
    """Get thread-local S3 client for concurrent uploads"""
    if not hasattr(thread_local, 's3_client'):
        thread_local.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=s3_config
        )
    return thread_local.s3_client

def get_video_info(video_path):
    """Get video information using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting video info for {video_path}: {e}")
        return None

def compress_video_h265_hevc(input_path, output_path, quality='medium', target_bitrate=None):
    """
    Compress video using H.265/HEVC codec (used by YouTube, Netflix)
    Quality options: 'fast', 'medium', 'slow', 'veryslow'
    """
    try:
        # Get video info to determine optimal settings
        video_info = get_video_info(input_path)
        if not video_info:
            return False
        
        # Extract video stream info
        video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        
        # Set quality presets based on resolution
        if width >= 1920:  # 1080p+
            crf = '23' if quality == 'fast' else '21' if quality == 'medium' else '19'
        elif width >= 1280:  # 720p
            crf = '25' if quality == 'fast' else '23' if quality == 'medium' else '21'
        else:  # 480p and below
            crf = '28' if quality == 'fast' else '26' if quality == 'medium' else '24'
        
        # Build ffmpeg command with H.265/HEVC
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx265',  # H.265/HEVC encoder
            '-preset', quality,
            '-crf', crf,
            '-c:a', 'aac',  # AAC audio codec
            '-b:a', '128k',  # Audio bitrate
            '-tag:v', 'hvc1',  # Apple compatibility
            '-pix_fmt', 'yuv420p',  # Compatibility
            '-movflags', '+faststart',  # Web optimization
            '-y', output_path
        ]
        
        # Add target bitrate if specified
        if target_bitrate:
            cmd.extend(['-b:v', target_bitrate])
        
        # Run compression
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
        
    except Exception as e:
        print(f"Error compressing video with H.265: {e}")
        return False

def compress_video_av1(input_path, output_path, quality='medium'):
    """
    Compress video using AV1 codec (next-gen codec used by YouTube, Netflix)
    AV1 provides 30% better compression than H.265
    """
    try:
        # Quality settings for AV1
        quality_map = {
            'fast': {'crf': '35', 'cpu-used': '8'},
            'medium': {'crf': '30', 'cpu-used': '4'},
            'slow': {'crf': '25', 'cpu-used': '2'},
            'veryslow': {'crf': '20', 'cpu-used': '0'}
        }
        
        settings = quality_map.get(quality, quality_map['medium'])
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libaom-av1',  # AV1 encoder
            '-crf', settings['crf'],
            '-cpu-used', settings['cpu-used'],
            '-row-mt', '1',  # Enable row-based multithreading
            '-tiles', '2x2',  # Tile encoding for better performance
            '-c:a', 'libopus',  # Opus audio (better than AAC)
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
        
    except Exception as e:
        print(f"Error compressing video with AV1: {e}")
        return False

def compress_video_vp9(input_path, output_path, quality='medium'):
    """
    Compress video using VP9 codec (used by YouTube for WebM)
    VP9 provides similar compression to H.265 with better web compatibility
    """
    try:
        # Quality settings for VP9
        quality_map = {
            'fast': {'crf': '35', 'cpu-used': '5'},
            'medium': {'crf': '30', 'cpu-used': '2'},
            'slow': {'crf': '25', 'cpu-used': '0'},
            'veryslow': {'crf': '20', 'cpu-used': '0'}
        }
        
        settings = quality_map.get(quality, quality_map['medium'])
        
        # Two-pass encoding for better quality
        # Pass 1
        cmd_pass1 = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libvpx-vp9',
            '-crf', settings['crf'],
            '-cpu-used', settings['cpu-used'],
            '-row-mt', '1',
            '-pass', '1',
            '-an',  # No audio in pass 1
            '-f', 'null',
            '/dev/null' if os.name != 'nt' else 'NUL'
        ]
        
        # Pass 2
        cmd_pass2 = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libvpx-vp9',
            '-crf', settings['crf'],
            '-cpu-used', settings['cpu-used'],
            '-row-mt', '1',
            '-pass', '2',
            '-c:a', 'libopus',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y', output_path
        ]
        
        # Run both passes
        subprocess.run(cmd_pass1, capture_output=True, text=True, check=True)
        subprocess.run(cmd_pass2, capture_output=True, text=True, check=True)
        
        # Clean up pass files
        for f in ['ffmpeg2pass-0.log', 'ffmpeg2pass-0.log.mbtree']:
            if os.path.exists(f):
                os.remove(f)
        
        return True
        
    except Exception as e:
        print(f"Error compressing video with VP9: {e}")
        return False

def compress_video_x264_advanced(input_path, output_path, quality='medium'):
    """
    Advanced H.264 compression using x264 with YouTube-optimized settings
    """
    try:
        # Get video info
        video_info = get_video_info(input_path)
        if not video_info:
            return False
        
        video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
        width = int(video_stream['width'])
        
        # YouTube-optimized x264 settings
        quality_map = {
            'fast': {'crf': '23', 'preset': 'fast'},
            'medium': {'crf': '21', 'preset': 'medium'},
            'slow': {'crf': '19', 'preset': 'slow'},
            'veryslow': {'crf': '17', 'preset': 'veryslow'}
        }
        
        settings = quality_map.get(quality, quality_map['medium'])
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',
            '-preset', settings['preset'],
            '-crf', settings['crf'],
            '-profile:v', 'high',
            '-level', '4.1',
            '-x264-params', 'ref=4:bframes=4:direct=auto:aq-mode=1:aq-strength=0.8:deblock=1,1',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-pix_fmt', 'yuv420p',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
        
    except Exception as e:
        print(f"Error compressing video with advanced x264: {e}")
        return False

def smart_compress_video(input_path, output_path=None, codec='auto', quality='medium', target_reduction=50):
    """
    Smart video compression that chooses the best codec and settings
    
    Args:
        input_path: Path to input video
        output_path: Path for compressed video (optional)
        codec: 'auto', 'h265', 'av1', 'vp9', 'x264'
        quality: 'fast', 'medium', 'slow', 'veryslow'
        target_reduction: Target size reduction percentage (10-90)
    """
    if output_path is None:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_compressed{ext}"
    
    # Get original file size
    original_size = os.path.getsize(input_path)
    print(f"Original size: {original_size / (1024*1024):.2f} MB")
    
    # Auto-select codec based on file size and requirements
    if codec == 'auto':
        if original_size > 500 * 1024 * 1024:  # > 500MB
            codec = 'h265'  # Best compression for large files
        elif original_size > 100 * 1024 * 1024:  # > 100MB
            codec = 'vp9'   # Good balance of compression and speed
        else:
            codec = 'x264'  # Fast for smaller files
    
    print(f"Using codec: {codec.upper()}")
    
    # Compress based on selected codec
    compression_functions = {
        'h265': compress_video_h265_hevc,
        'av1': compress_video_av1,
        'vp9': compress_video_vp9,
        'x264': compress_video_x264_advanced
    }
    
    compression_func = compression_functions.get(codec)
    if not compression_func:
        print(f"Unsupported codec: {codec}")
        return False
    
    # Try compression
    success = compression_func(input_path, output_path, quality)
    
    if success and os.path.exists(output_path):
        compressed_size = os.path.getsize(output_path)
        reduction = ((original_size - compressed_size) / original_size) * 100
        print(f"Compressed size: {compressed_size / (1024*1024):.2f} MB")
        print(f"Size reduction: {reduction:.1f}%")
        
        # If compression didn't meet target, try more aggressive settings
        if reduction < target_reduction and quality != 'veryslow':
            print(f"Target reduction not met ({reduction:.1f}% < {target_reduction}%), trying higher compression...")
            backup_path = output_path + '.backup'
            shutil.move(output_path, backup_path)
            
            # Try with higher compression
            next_quality = {'fast': 'medium', 'medium': 'slow', 'slow': 'veryslow'}.get(quality, 'veryslow')
            success = compression_func(input_path, output_path, next_quality)
            
            if success:
                new_compressed_size = os.path.getsize(output_path)
                new_reduction = ((original_size - new_compressed_size) / original_size) * 100
                print(f"New compressed size: {new_compressed_size / (1024*1024):.2f} MB")
                print(f"New size reduction: {new_reduction:.1f}%")
                os.remove(backup_path)
            else:
                shutil.move(backup_path, output_path)
        
        return True
    
    return False

def upload_video_to_s3(local_path, s3_filename=None, use_multipart=True):
    """
    Uploads a local video file to S3 with optimizations and returns the public URL.
    """
    if s3_filename is None:
        s3_filename = os.path.basename(local_path)
    
    try:
        client = get_s3_client()
        
        # Get file size to decide upload method
        file_size = os.path.getsize(local_path)
        
        # Use multipart upload for files larger than 100MB
        if use_multipart and file_size > 100 * 1024 * 1024:
            # Configure multipart upload
            config = boto3.s3.transfer.TransferConfig(
                multipart_threshold=1024 * 25,  # 25MB
                max_concurrency=10,
                multipart_chunksize=1024 * 25,
                use_threads=True
            )
            
            # Use S3 Transfer Manager for optimized uploads
            transfer = boto3.s3.transfer.S3Transfer(client, config)
            transfer.upload_file(
                local_path, 
                AWS_S3_BUCKET, 
                s3_filename,
                extra_args={'ACL': 'public-read'}
            )
        else:
            # Standard upload for smaller files
            client.upload_file(
                local_path, 
                AWS_S3_BUCKET, 
                s3_filename, 
                ExtraArgs={'ACL': 'public-read'}
            )
        
        # Generate URL based on region
        if AWS_S3_REGION == 'us-east-1':
            url = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_filename}"
        else:
            url = f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{s3_filename}"
        
        return url
        
    except Exception as e:
        print(f"Failed to upload {local_path} to S3: {e}")
        return None

def upload_single_video(args):
    """Helper function for concurrent uploads"""
    folder, filename = args
    local_path = os.path.join(folder, filename)
    url = upload_video_to_s3(local_path, s3_filename=filename)
    
    if url:
        print(f"Uploaded {filename} to {url}")
        return {'filename': filename, 'url': url}
    else:
        print(f"Failed to upload {filename}")
        return None

def upload_all_videos_in_surveillance_outputs(max_workers=5):
    """
    Uploads all video files from the surveillance_outputs folder to S3 concurrently.
    Returns a list of their public URLs.
    """
    folder = 'surveillance_outputs'
    uploaded_urls = []
    
    if not os.path.exists(folder):
        print(f"Folder '{folder}' does not exist.")
        return uploaded_urls
    
    # Get all MP4 files
    video_files = [f for f in os.listdir(folder) if f.lower().endswith('.mp4')]
    
    if not video_files:
        print("No MP4 files found in surveillance_outputs folder.")
        return uploaded_urls
    
    print(f"Found {len(video_files)} video files to upload.")
    
    # Use ThreadPoolExecutor for concurrent uploads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Prepare arguments for each upload
        upload_args = [(folder, filename) for filename in video_files]
        
        # Submit all upload tasks
        future_to_filename = {
            executor.submit(upload_single_video, args): args[1] 
            for args in upload_args
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_filename):
            filename = future_to_filename[future]
            try:
                result = future.result()
                if result:
                    uploaded_urls.append(result)
            except Exception as e:
                print(f"Upload failed for {filename}: {e}")
    
    print(f"Successfully uploaded {len(uploaded_urls)} out of {len(video_files)} videos.")
    return uploaded_urls

def upload_video_with_progress(local_path, s3_filename=None, callback=None):
    """
    Upload with progress tracking (optional enhancement)
    """
    if s3_filename is None:
        s3_filename = os.path.basename(local_path)
    
    try:
        client = get_s3_client()
        file_size = os.path.getsize(local_path)
        
        # Create a progress callback if provided
        if callback:
            def progress_callback(bytes_transferred):
                percentage = (bytes_transferred / file_size) * 100
                callback(percentage, bytes_transferred, file_size)
        
        # Configure transfer with progress callback
        config = boto3.s3.transfer.TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )
        
        transfer = boto3.s3.transfer.S3Transfer(client, config)
        transfer.upload_file(
            local_path,
            AWS_S3_BUCKET,
            s3_filename,
            extra_args={'ACL': 'public-read'},
            callback=progress_callback if callback else None
        )
        
        url = f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{s3_filename}"
        return url
        
    except Exception as e:
        print(f"Failed to upload {local_path} to S3: {e}")
        return None

def log_detection_event(entry_time, exit_time, video_url, sms_sent=True):
    """Enhanced logging function"""
    event = {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "video_url": video_url,
        "sms_sent": sms_sent,
        "timestamp": datetime.datetime.now()
    }
    # Log to file for persistence
    log_filename = f"detection_events_{datetime.datetime.now().strftime('%Y%m%d')}.log"
    with open(log_filename, 'a') as f:
        f.write(f"{event}\n")
    print(f"Logging event: {event}")
    return event

# Example usage with progress tracking
def example_upload_with_progress():
    def progress_callback(percentage, bytes_transferred, total_bytes):
        print(f"Upload progress: {percentage:.1f}% ({bytes_transferred}/{total_bytes} bytes)")
    
    # Upload single file with progress
    url = upload_video_with_progress("path/to/video.mp4", callback=progress_callback)
    if url:
        print(f"Upload completed: {url}")
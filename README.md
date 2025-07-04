# 🚨 Advanced Person Detection Surveillance System

A modern, real-time surveillance system using YOLOv8 and ByteTracker for accurate person detection and tracking. Features a Gradio web interface, Twilio SMS alerts, GPU acceleration support, and automatic saving of output video during detection events.

---

## ✨ Features
- **YOLOv8 Person Detection**: Fast and accurate detection using Ultralytics YOLOv8.
- **ByteTracker Multi-Object Tracking**: Robust tracking of multiple people in the frame.
- **Live Web Interface**: Control and monitor your system from any browser using Gradio.
- **Camera Flexibility**: Supports Laptop Camera, Android IP Camera, and custom RTSP/HTTP streams.
- **Twilio SMS Alerts**: Get instant notifications when someone enters or leaves the monitored area.
- **GPU Acceleration**: Automatically uses your NVIDIA GPU for maximum performance (if available).
- **Customizable Settings**: Adjust detection confidence, area threshold, patience, and more from the UI.
- **Automatic Video Saving**: Output video during detection events is automatically saved on your device for later review in a folder named `surveillance_outputs` (created automatically if it doesn't exist).
- **Amazon S3 Cloud Upload**: After each detection event, the recorded video is uploaded from the local `surveillance_outputs` folder to your configured Amazon S3 bucket using `boto3`. The public S3 URL for each video is sent to you via Twilio SMS for instant remote access, so you can view your surveillance videos from anywhere.
- **Advanced Video Compression**: Videos are automatically compressed before upload using smart, multi-codec compression (H.265/HEVC, AV1, VP9, and advanced H.264/x264) for optimal quality and size. The system auto-selects the best codec and compression level based on file size and your target reduction.
- **Concurrent & Optimized S3 Uploads**: Supports multi-threaded, thread-safe, and multipart S3 uploads for fast, reliable cloud storage. Batch upload all videos in `surveillance_outputs` with a single function call. Upload progress tracking is available.
- **Detection Event Logging**: All detection events (entry/exit times, video URL, SMS status) are logged to a daily log file for audit and review.

---

## 🚀 Quick Start

### 1. Clone the Repository
```sh
git clone https://github.com/adityapawar327/Surveillance_System.git
cd Surveillance_System
```

### 2. Install Requirements
Make sure you have Python 3.9+ and pip installed.
```sh
pip install -r requirements.txt
```

### 3. Download YOLOv8n Weights
The first run will automatically download `yolov8n.pt` if not present.

### 4. Run the App
```sh
python app.py
```

- Access the web UI at: [http://localhost:7860](http://localhost:7860)

---

## ☁️ Cloud Video Storage with Amazon S3
- **Automatic S3 Upload**: After each detection event, the recorded video is uploaded from the local `surveillance_outputs` folder to your configured Amazon S3 bucket using `boto3`.
- **Public Video Links**: The S3 public URL for each video is sent to you via Twilio SMS for instant remote access.
- **Batch Upload & Concurrency**: Upload all videos in the `surveillance_outputs` folder to S3 concurrently using the provided utility function. Large files use optimized multipart upload for speed and reliability.
- **Upload Progress Tracking**: Optional progress callback for real-time upload feedback.

### S3 & Compression Setup
1. Add your AWS credentials and bucket info to the `.env` file:
   ```env
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   AWS_S3_BUCKET=your-bucket-name
   AWS_S3_REGION=your-region
   ```
2. Install requirements:
   ```sh
   pip install -r requirements.txt
   ```
3. Videos are automatically compressed and uploaded after each event. You can use the `upload_all_videos_in_surveillance_outputs()` function to upload all existing videos, or `smart_compress_video()` to compress any video with optimal settings.

#### Example: Smart Compression & Upload
```python
from database import smart_compress_video, upload_video_to_s3

# Compress a video with smart settings
temp_path = 'surveillance_outputs/event1.mp4'
smart_compress_video(temp_path)

# Upload to S3
url = upload_video_to_s3(temp_path)
print('S3 URL:', url)
```

---

## 📷 Camera Setup
- **Laptop Camera**: Uses your built-in webcam (index 0).
- **Android IP Camera**: Use the [IP Webcam app](https://play.google.com/store/apps/details?id=com.pas.webcam) and set the IP in the UI (default: `192.168.0.101:8080`).
- **Custom URL**: Enter any RTSP/HTTP stream URL.

---

## 📱 SMS Alerts (Twilio)
1. [Sign up for Twilio](https://www.twilio.com/try-twilio) and get your Account SID, Auth Token, and phone numbers.
2. Enter your credentials in the "SMS Alerts" tab in the web UI.
3. Click "Setup SMS Alerts" and test with "Send Test SMS".

---

## ⚙️ Settings
- **Detection Confidence**: Higher = fewer false positives.
- **Minimum Person Area**: Filter out small detections.
- **Exit Patience**: Time to wait before confirming a person has left.
- **Detection Threshold**: Frames needed to confirm presence.

---

## 🖥️ GPU Acceleration
- Make sure you have an NVIDIA GPU and the correct CUDA drivers.
- The app will use your GPU automatically if available (see logs for confirmation).
- If you see `YOLOv8 is running on CPU!`, check your CUDA/PyTorch installation.

---

## 🛠️ Troubleshooting
- **Camera not working?**
  - Check permissions, close other apps, try a different index, or check your drivers.
- **YOLOv8 on CPU?**
  - Ensure you installed the correct CUDA-enabled PyTorch version (see `requirements.txt`).
- **SMS not sending?**
  - Double-check Twilio credentials and phone numbers.

---

## 📂 Project Structure
```
├── app.py                # Gradio web interface
├── detection_system.py   # Detection and tracking logic
├── database.py           # Video compression, S3 upload, logging utilities
├── requirements.txt      # All dependencies
├── README.md             # This file
└── yolov8n.pt            # YOLOv8n weights (auto-downloaded)
```

---

## 🤝 Contributing
Pull requests and suggestions are welcome! Please open an issue or PR.

---

## 📄 License
MIT License

---

## 🙏 Credits
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- [Supervision/ByteTrack](https://github.com/roboflow/supervision)
- [Gradio](https://gradio.app/)
- [Twilio](https://www.twilio.com/)

---

## 🖼️ Screenshots


![ ](screenshots/Screenshot%202025-07-04%20194155.png)

![ ](screenshots/Screenshot%202025-07-04%20194243.png)

![ ](screenshots/Screenshot%202025-07-04%20193036.png)


---

## ⚠️ Why Isn't This Deployed Online?
This project is not deployed as a public web app for the following reasons:

- **Deep Learning & GPU Acceleration**: The system relies on real-time deep learning inference (YOLOv8) and multi-object tracking, which require significant computational resources. Free or low-cost cloud servers typically do not provide the necessary GPU acceleration, resulting in poor performance or inability to run the model at all.
- **Security & Privacy**: Surveillance systems process sensitive video feeds. For privacy and security, it is strongly recommended to run this application locally on your own trusted hardware, rather than uploading your camera streams to a third-party server.

---

## 🖥️ System Requirements & Installation

### Minimum System Requirements
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS (limited, CPU only)
- **Python**: Version 3.9 or higher
- **RAM**: 8 GB (16 GB recommended for smooth operation)
- **GPU**: NVIDIA GPU with CUDA support (recommended for real-time performance)
- **CUDA Toolkit**: Properly installed CUDA drivers (if using GPU)
- **Free Disk Space**: At least 2 GB for dependencies and video outputs

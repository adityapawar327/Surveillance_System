# Advanced Person Detection Surveillance System

A modern, real-time surveillance system for accurate person detection, tracking, and event-based video management. Features a web interface, cloud storage, SMS alerts, advanced video compression, and robust logging.

---

## ✨ Features
- **YOLOv8 Person Detection**: Fast, accurate detection using Ultralytics YOLOv8.
- **ByteTrack Multi-Object Tracking**: Robust tracking of multiple people in the frame.
- **Live Web Interface**: Control and monitor your system from any browser using Gradio.
- **Flexible Camera Support**: Use a laptop webcam, Android IP camera, or any RTSP/HTTP stream.
- **Twilio SMS Alerts**: Instant notifications when someone enters or leaves the monitored area.
- **GPU Acceleration**: Automatic use of NVIDIA GPU for maximum performance (if available).
- **Customizable Detection Settings**: Adjust detection confidence, area threshold, patience, and more from the UI.
- **Automatic Video Saving**: Event-based video recording, saved in `surveillance_outputs`.
- **Advanced Video Compression**: Smart, multi-codec compression (H.265/HEVC, AV1, VP9, x264) for optimal size and quality.
- **Automatic S3 Cloud Upload**: Compressed videos are uploaded to your Amazon S3 bucket after each event. Public S3 URLs are sent via SMS and logged.
- **Concurrent & Optimized S3 Uploads**: Multi-threaded, thread-safe, and multipart S3 uploads for speed and reliability. Batch upload and progress tracking supported.
- **Detection Event Logging**: All detection events (entry/exit, video URL, SMS status) are logged to a daily file for audit and review.

---

## 🖼️ Demo Screenshots
![Login Page](screenshots/Screenshot%202025-07-04%20194243.png)
![SMS Setup](screenshots/Screenshot%202025-07-04%20194155.png)
![Live Detection](screenshots/Screenshot%202025-07-04%20193036.png)

---

## 🚀 Quick Start

1. **Clone the Repository**
   ```sh
   git clone https://github.com/adityapawar327/Surveillance_System.git
   cd Surveillance_System
   ```
2. **Install Requirements**
   ```sh
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**
   - Copy the sample below to a `.env` file in the project root and fill in your values.
4. **Run the App**
   ```sh
   python app.py
   ```
   - Access the web UI at: [http://localhost:7860](http://localhost:7860)

---

## 🛠️ Environment Variables (.env Sample)

> **Where to get these values:**
> - [AWS Access Keys & S3 Setup](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html)
> - [Twilio Account SID & Auth Token](https://www.twilio.com/console)
> - [Twilio Phone Numbers](https://www.twilio.com/console/phone-numbers/incoming)
> - [Android IP Webcam App](https://play.google.com/store/apps/details?id=com.pas.webcam)

```env
# AWS S3 (Cloud Storage)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_S3_BUCKET=your-bucket-name
AWS_S3_REGION=your-region

# Twilio (SMS Alerts)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_YOUR_NUM=+1234567890
TWILIO_TWILIO_NUM=+1234567890

# Android IP Camera (optional)
ANDROID_IP_CAMERA_URL=http://192.168.0.101:8080/video
```

---

## ⚙️ Configuration & Usage

### Camera Setup
- **Laptop Camera**: Uses your built-in webcam (index 0).
- **Android IP Camera**: Use the [IP Webcam app](https://play.google.com/store/apps/details?id=com.pas.webcam) and set the IP in the UI or `.env`.
- **Custom URL**: Enter any RTSP/HTTP stream URL in the UI.

### Detection Settings
- **Detection Confidence**: Higher = fewer false positives.
- **Minimum Person Area**: Filter out small detections.
- **Exit Patience**: Time to wait before confirming a person has left.
- **Detection Threshold**: Frames needed to confirm presence.

### Cloud Storage (Amazon S3)
- **Automatic Upload**: After each detection event, the compressed video is uploaded to S3. The public URL is sent via SMS and logged.
- **Batch Upload**: Use `upload_all_videos_in_surveillance_outputs()` to upload all videos in `surveillance_outputs`.
- **Progress Tracking**: Use `upload_video_with_progress()` for real-time upload feedback.

### SMS Alerts (Twilio)
- **Setup**: Enter your Twilio credentials in the UI or `.env`.
- **Test**: Use the "Send Test SMS" button in the UI.

### Video Compression
- **Smart Compression**: Videos are compressed using the best codec for size/quality before upload.
- **Manual Compression**: Use `smart_compress_video()` for any video file.

### Logging
- **Event Logging**: All detection events are logged to a daily file (e.g., `detection_events_YYYYMMDD.log`).

---

## 📂 Project Structure
```
├── app.py                # Gradio web interface
├── detection_system.py   # Detection, tracking, and event logic
├── database.py           # Video compression, S3 upload, logging utilities
├── requirements.txt      # All dependencies
├── README.md             # This file
├── yolov8n.pt            # YOLOv8n weights (auto-downloaded)
├── surveillance_outputs/ # Saved event videos
├── screenshots/          # UI screenshots
```

---

## 🖥️ System Requirements
- **OS**: Windows 10/11, Ubuntu 20.04+, or macOS (CPU only)
- **Python**: 3.9 or higher
- **RAM**: 8 GB (16 GB recommended)
- **GPU**: NVIDIA GPU with CUDA (recommended)
- **CUDA Toolkit**: Properly installed (if using GPU)
- **Disk Space**: 2 GB+ for dependencies and video outputs

---

## 🛠️ Troubleshooting
- **Camera not working?** Check permissions, close other apps, try a different index, or check drivers.
- **YOLOv8 on CPU?** Ensure you installed the correct CUDA-enabled PyTorch version.
- **SMS not sending?** Double-check Twilio credentials and phone numbers.
- **S3 Upload Fails?** Check your AWS credentials and bucket permissions.

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

## ❓ FAQ / Why Not Deployed Online?
- **Deep Learning & GPU**: Real-time inference and tracking require significant compute. Most cloud servers lack the necessary GPU acceleration.
- **Security & Privacy**: Surveillance systems process sensitive video feeds. For privacy, run this application locally on trusted hardware.

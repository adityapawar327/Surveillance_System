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
- **Automatic Video Saving**: Output video during detection events is automatically saved on your device for later review.

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

### Login Page
![Login Page](screenshots/3_login.png)

### Live Detection & Analytics
![Live Detection](screenshots/1_live_detection.png)

### SMS Alerts Configuration
![SMS Alerts](screenshots/2_sms_alerts.png)

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

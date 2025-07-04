from detection_system import AdvancedPersonDetectionSystem
from database import log_detection_event, smart_compress_video, upload_video_to_s3
import gradio as gr
import datetime
from collections import deque

# Initialize the detection system
detector = AdvancedPersonDetectionSystem()

def setup_twilio_wrapper(account_sid, auth_token, your_num, twilio_num):
    return detector.setup_twilio(account_sid, auth_token, your_num, twilio_num)

def start_detection(camera_type, custom_url):
    success, message = detector.start_camera(camera_type, custom_url)
    if success:
        detector.running = True
    return message

def stop_detection():
    return detector.stop_camera()

def update_settings(confidence, area_threshold, patience, detection_thresh):
    detector.confidence_threshold = confidence
    detector.area_threshold = int(area_threshold)
    detector.patience = patience
    detector.detection_thresh = int(detection_thresh)
    detector.de = deque([False] * detector.detection_thresh, maxlen=detector.detection_thresh)
    return "Settings updated successfully!"

def get_frame():
    """Get current frame and status"""
    import platform
    import subprocess
    cpu_info = platform.processor() or platform.machine()
    gpu_info = "Unknown"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info = torch.cuda.get_device_name(0)
        else:
            try:
                result = subprocess.check_output(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], encoding='utf-8')
                gpu_info = result.strip().split('\n')[0]
            except Exception:
                gpu_info = "No GPU detected"
    except Exception:
        gpu_info = "PyTorch not installed"
    if detector.running and detector.cap and detector.cap.isOpened():
        frame, status = detector.process_frame()
        if frame is not None:
            # Add CPU and GPU info to the analytics
            status["🖥️ CPU Info"] = cpu_info
            status["🖥️ GPU Info"] = gpu_info
            return frame, status
        else:
            status["🖥️ CPU Info"] = cpu_info
            status["🖥️ GPU Info"] = gpu_info
            return None, status
    # Show all analytics fields even if camera is not running
    return None, {
        "🏠 Room Occupied": False,
        "👥 Current Persons": 0,
        "📊 Detection Score": "0/8",
        "📈 Total Detections": 0,
        "📹 Recording": False,
        "🎯 FPS": 0,
        "📱 SMS Alerts": detector.twilio_enabled,
        "🔧 Model": "YOLOv8",
        "⚡ Confidence": detector.confidence_threshold,
        "🎚️ Area Threshold": detector.area_threshold,
        "📷 Camera Source": "Not Connected",
        "✅ Status": "Stopped",
        "🖥️ CPU Info": cpu_info,
        "🖥️ GPU Info": gpu_info
    }

def test_sms():
    if detector.twilio_enabled:
        test_message = f"🧪 Test Alert from Surveillance System\n⏰ {datetime.datetime.now().strftime('%I:%M:%S %p %d %B %Y')}"
        return detector.send_message(test_message)
    return "Twilio not configured"

def toggle_custom_url(camera_type):
    """Show/hide custom URL input based on camera selection"""
    return gr.update(visible=(camera_type == "Custom URL"))

# Create advanced Gradio interface
with gr.Blocks(title="Advanced Person Detection with YOLO", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🤖 Advanced Person Detection Surveillance System")
    gr.Markdown("Powered by **YOLOv8** and **ByteTracker** for superior accuracy and performance")
    
    with gr.Tab("🎥 Live Detection"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📹 Camera Setup")
                
                camera_type = gr.Radio(
                    choices=[
                        "Laptop Camera", 
                        "Android IP Camera (Default)", 
                        "Custom URL"
                    ],
                    value="Laptop Camera",  # Changed default to laptop camera
                    label="Camera Source",
                    info="Select your preferred camera source"
                )
                
                custom_url_input = gr.Textbox(
                    label="Custom Camera URL",
                    placeholder="Enter full URL (e.g., http://192.168.1.5:8080/video)",
                    visible=False,
                    info="Only visible when 'Custom URL' is selected"
                )
                
                gr.Markdown("### 📋 Camera Sources:")
                gr.Markdown("""
                - **Laptop Camera**: Built-in webcam (recommended for testing)
                - **Android IP Camera**: http://192.168.1.3:8080/video
                - **Custom URL**: Enter your own camera stream URL
                """)
                
                with gr.Row():
                    start_btn = gr.Button("🚀 Start Detection", variant="primary", size="lg")
                    stop_btn = gr.Button("⏹️ Stop Detection", variant="secondary", size="lg")
                
                status_output = gr.Textbox(label="System Status", interactive=False)
                
                gr.Markdown("## ⚙️ Detection Settings")
                confidence_slider = gr.Slider(
                    minimum=0.1, maximum=1.0, value=0.5, step=0.05,
                    label="Detection Confidence", info="Higher = fewer false positives"
                )
                area_threshold_slider = gr.Slider(
                    minimum=500, maximum=10000, value=2000, step=100,
                    label="Minimum Person Area", info="Pixels squared"
                )
                patience_slider = gr.Slider(
                    minimum=1, maximum=20, value=5, step=1,
                    label="Exit Patience (seconds)", info="Wait time before confirming exit"
                )
                detection_threshold_slider = gr.Slider(
                    minimum=3, maximum=20, value=8, step=1,
                    label="Detection Threshold", info="Frames needed to confirm presence"
                )
                
                update_settings_btn = gr.Button("💾 Update Settings", variant="secondary")
                settings_status = gr.Textbox(label="Settings Status", interactive=False)
                
            with gr.Column(scale=2):
                gr.Markdown("## 📊 Live Feed & Analytics")
                video_output = gr.Image(label="🎥 Live Video Feed", height=400)
                
                status_json = gr.JSON(label="📈 Real-time Analytics", value={
                    "🏠 Room Occupied": False,
                    "👥 Current Persons": 0,
                    "📊 Detection Score": "0/8",
                    "📈 Total Detections": 0,
                    "📹 Recording": False,
                    "🎯 FPS": 0,
                    "📱 SMS Alerts": False,
                    "🔧 Model": "YOLOv8",
                    "⚡ Confidence": 0.5,
                    "🎚️ Area Threshold": 2000,
                    "📷 Camera Source": "Not Connected",
                    "✅ Status": "Stopped",
                    "🖥️ CPU Info": "Fetching...",
                    "🖥️ GPU Info": "Fetching..."
                })
    
    with gr.Tab("📱 SMS Alerts"):
        gr.Markdown("## 📱 Twilio SMS Configuration")
        gr.Markdown("Get instant notifications when people enter or leave the monitored area.")
        
        with gr.Row():
            with gr.Column():
                account_sid_input = gr.Textbox(label="Account SID", type="password")
                auth_token_input = gr.Textbox(label="Auth Token", type="password")
            with gr.Column():
                your_num_input = gr.Textbox(label="Your Phone Number", placeholder="+1234567890")
                twilio_num_input = gr.Textbox(label="Twilio Phone Number", placeholder="+1234567890")
        
        with gr.Row():
            setup_twilio_btn = gr.Button("📱 Setup SMS Alerts", variant="primary")
            test_sms_btn = gr.Button("🧪 Send Test SMS", variant="secondary")
        
        twilio_status = gr.Textbox(label="SMS Status", interactive=False)
    
    with gr.Tab("🔧 Troubleshooting"):
        gr.Markdown("## 🔧 Troubleshooting Guide")
        gr.Markdown("""
        ### 📷 **Camera Issues**
        
        #### ❌ **Laptop Camera Not Working**
        1. **Check Camera Permissions**: Ensure the app has camera access
        2. **Close Other Apps**: Close Zoom, Skype, or other camera apps
        3. **Try Different Index**: Some laptops use index 1 instead of 0
        4. **Check Device Manager**: Ensure camera driver is working
        
        #### ❌ **Live Feed Not Showing**
        1. **Start Camera First**: Click "Start Detection" before expecting feed
        2. **Check Browser**: Some browsers block camera access
        3. **Refresh Page**: Try refreshing the browser tab
        4. **Check Console**: Look for error messages in browser console
        
        #### ❌ **IP Camera Issues**
        - **Network**: Ensure phone and computer are on same WiFi
        - **URL Format**: Use `http://IP:8080/video` (include /video)
        - **Firewall**: Check if firewall is blocking connection
        - **App Settings**: Ensure IP Webcam app is running on phone
        
        ### 🤖 **Model Issues**
        - **YOLO Download**: First run downloads YOLOv8 model (~6MB)
        - **Internet Required**: Initial model download needs internet
        - **Storage Space**: Ensure sufficient disk space for model files
        
        ### 📱 **SMS Issues**
        - **Twilio Account**: Need valid Twilio account with credits
        - **Phone Numbers**: Use international format (+1234567890)
        - **Credentials**: Double-check Account SID and Auth Token
        
        ### 🚀 **Performance Tips**
        - **Lower Settings**: Reduce confidence threshold for faster detection
        - **Camera Resolution**: Lower resolution = better performance
        - **Close Background Apps**: Free up system resources
        """)
    
    # Event handlers
    camera_type.change(
        fn=toggle_custom_url,
        inputs=[camera_type],
        outputs=[custom_url_input]
    )
    
    start_btn.click(
        fn=start_detection,
        inputs=[camera_type, custom_url_input],
        outputs=[status_output]
    )
    
    stop_btn.click(
        fn=stop_detection,
        outputs=[status_output]
    )
    
    setup_twilio_btn.click(
        fn=setup_twilio_wrapper,
        inputs=[account_sid_input, auth_token_input, your_num_input, twilio_num_input],
        outputs=[twilio_status]
    )
    
    test_sms_btn.click(
        fn=test_sms,
        outputs=[twilio_status]
    )
    
    update_settings_btn.click(
        fn=update_settings,
        inputs=[confidence_slider, area_threshold_slider, patience_slider, detection_threshold_slider],
        outputs=[settings_status]
    )
    
    # Manual refresh for video feed - removed streaming for better compatibility
    def refresh_feed():
        return get_frame()
    
    # Auto-refresh every 100ms when running
    timer = gr.Timer(value=0.1)
    timer.tick(
        fn=get_frame,
        outputs=[video_output, status_json]
    )

if __name__ == "__main__":
    # Check for required packages
    try:
        import ultralytics
        import supervision
        print("✅ All required packages are available")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please install: pip install ultralytics supervision")
    
    print("🚀 Starting Advanced Person Detection System...")
    print("📹 Default camera source: Laptop Camera")
    print("🌐 Access the interface at: http://localhost:7860")
    
    app.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=True,  # Enable public link
        show_error=True,
        debug=True,  # Added debug mode
        auth=[
            ("admin", "admin123"),
            ("user", "user123")
        ]
    )
import numpy as np
import cv2
import time
import datetime
from collections import deque
import os
from twilio.rest import Client
from ultralytics import YOLO
import supervision as sv
from supervision import ByteTrack, Detections
import logging
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
ANDROID_IP_CAMERA_URL = os.getenv("ANDROID_IP_CAMERA_URL", "http://192.168.0.101:8080/video")

class AdvancedPersonDetectionSystem:
    def __init__(self):
        # Camera and recording
        self.cap = None
        self.out = None
        self.running = False
        self.current_frame = None
        # Detection parameters
        self.confidence_threshold = 0.5
        self.person_class_id = 0  # COCO person class
        self.detection_thresh = 8
        self.patience = 5
        self.area_threshold = 2000
        # State tracking
        self.status = False
        self.initial_time = None
        self.de = deque([False] * self.detection_thresh, maxlen=self.detection_thresh)
        self.person_count_history = deque(maxlen=30)
        self.detection_count = 0
        self.entry_time = None
        # ML Models
        self.yolo_model = None
        self.tracker = None
        self.person_tracker = {}
        self.next_person_id = 1
        # Twilio settings
        self.twilio_enabled = False
        self.account_sid = ""
        self.auth_token = ""
        self.your_num = ""
        self.twilio_num = ""
        # Output directory
        self.output_dir = 'surveillance_outputs'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        # Performance metrics
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        # Alert system
        self.last_alert_time = 0
        self.alert_cooldown = 300
        # Camera settings
        self.current_camera_source = None
        # Frame processing settings
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        self.frame_thread = None
        self.stop_thread = False
        self.frame_skip = 1  # Process every frame for max FPS
        self.resize_width = 1920  # 1080p width
        self.resize_height = 1080  # 1080p height
        # Initialize models
        self.initialize_models()
        self.android_ip_camera_url = ANDROID_IP_CAMERA_URL

    def initialize_models(self):
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            device = 'cuda' if cuda_available else 'cpu'
            logging.info(f"torch.cuda.is_available(): {cuda_available}")
            self.yolo_model = YOLO('yolov8n.pt')
            self.yolo_model.to(device)
            # Log model device
            try:
                model_device = next(self.yolo_model.model.parameters()).device
                logging.info(f"YOLO model device after .to(): {model_device}")
            except Exception as e:
                logging.warning(f"Could not determine YOLO model device: {e}")
            # Ensure tracker is initialized only if supervision is available and no error
            try:
                self.tracker = ByteTrack()
            except Exception as e:
                self.tracker = None
                logging.error(f"Failed to initialize ByteTrack: {e}")
            if self.tracker is None:
                logging.error("ByteTracker is not initialized!")
            logging.info(f"YOLO model loaded successfully on {device.upper()}")
            if not cuda_available:
                logging.warning("CUDA is NOT available! YOLOv8 will run on CPU. Performance will be low.")
            return True, f"YOLO model initialized on {device.upper()}"
        except Exception as e:
            self.tracker = None
            logging.error(f"Failed to initialize models: {e}")
            return False, f"Model initialization failed: {str(e)}"

    def setup_twilio(self, account_sid, auth_token, your_num, twilio_num):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.your_num = your_num
        self.twilio_num = twilio_num
        self.twilio_enabled = bool(account_sid and auth_token and your_num and twilio_num)
        return "Twilio configured successfully!" if self.twilio_enabled else "Twilio configuration incomplete"

    def send_message(self, body):
        if not self.twilio_enabled:
            return "Twilio not configured"
        current_time = time.time()
        if current_time - self.last_alert_time < self.alert_cooldown:
            return "Alert cooldown active"
        try:
            client = Client(self.account_sid, self.auth_token)
            message = client.messages.create(
                to=self.your_num,
                from_=self.twilio_num,
                body=body
            )
            self.last_alert_time = current_time
            return f"Message sent successfully: {message.sid}"
        except Exception as e:
            logging.error(f"Failed to send message: {e}")
            return f"Failed to send message: {str(e)}"

    def detect_persons_yolo(self, frame):
        if self.yolo_model is None:
            return [], frame
        try:
            results = self.yolo_model(frame, verbose=False)
            detections = []
            annotated_frame = frame.copy()
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for i in range(len(boxes)):
                    box = boxes.xyxy[i].cpu().numpy()
                    conf = boxes.conf[i].cpu().numpy()
                    cls = boxes.cls[i].cpu().numpy()
                    if int(cls) == self.person_class_id and conf > self.confidence_threshold:
                        x1, y1, x2, y2 = map(int, box)
                        area = (x2 - x1) * (y2 - y1)
                        if area > self.area_threshold:
                            detections.append({
                                'bbox': [x1, y1, x2, y2],
                                'confidence': float(conf),
                                'area': area,
                                'center': ((x1 + x2) // 2, (y1 + y2) // 2)
                            })
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(annotated_frame, f'Person {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            center = ((x1 + x2) // 2, (y1 + y2) // 2)
                            cv2.circle(annotated_frame, center, 5, (255, 0, 0), -1)
            return detections, annotated_frame
        except Exception as e:
            logging.error(f"YOLO detection error: {e}")
            return [], frame

    def track_persons(self, detections, frame):
        if not self.tracker:
            logging.error("Tracker is not initialized.")
            return frame, 0
        if not detections:
            return frame, 0
        try:
            detection_array = np.array([[d['bbox'][0], d['bbox'][1], d['bbox'][2], d['bbox'][3], d['confidence']] for d in detections])
            tracked_objects = self.tracker.update(
                Detections(xyxy=detection_array[:, :4], confidence=detection_array[:, 4])
            )
            for i in range(len(tracked_objects)):
                x1, y1, x2, y2 = map(int, tracked_objects.xyxy[i])
                track_id = tracked_objects.tracker_id[i] if hasattr(tracked_objects, 'tracker_id') and tracked_objects.tracker_id is not None else i
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
                cv2.putText(frame, f'ID: {track_id}', (x1, y2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            return frame, len(detections)
        except Exception as e:
            logging.error(f"Tracking error: {e}")
            return frame, len(detections)

    def apply_smart_filtering(self, person_count):
        self.person_count_history.append(person_count)
        if len(self.person_count_history) < 5:
            return person_count > 0
        recent_counts = list(self.person_count_history)[-5:]
        median_count = np.median(recent_counts)
        return median_count > 0

    def get_camera_source(self, source_type, custom_url=""):
        if source_type == "Laptop Camera":
            return 0
        elif source_type == "Android IP Camera (Default)":
            # Use the IP from .env
            return self.android_ip_camera_url
        elif source_type == "Custom URL":
            # Use the provided custom URL, fallback to Android IP if empty
            return custom_url if custom_url else self.android_ip_camera_url
        else:
            return 0

    def threaded_frame_grabber(self):
        while not self.stop_thread and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logging.warning("Frame grabber: Failed to read frame. Stopping thread.")
                    break
                with self.frame_lock:
                    self.latest_frame = frame.copy()
            except cv2.error as e:
                logging.error(f"OpenCV error in frame grabber: {e}")
                break
            except Exception as e:
                logging.error(f"Unknown error in frame grabber: {e}")
                break
            time.sleep(0.01)  # Small sleep to reduce CPU usage

    def start_camera(self, source_type, custom_url=""):
        try:
            camera_source = self.get_camera_source(source_type, custom_url)
            self.current_camera_source = camera_source
            if isinstance(camera_source, str) and camera_source.isdigit():
                camera_source = int(camera_source)
            if self.cap:
                self.cap.release()
                time.sleep(0.5)
            if camera_source == 0:
                backends = [cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_ANY]
                for backend in backends:
                    try:
                        self.cap = cv2.VideoCapture(camera_source, backend)
                        if self.cap.isOpened():
                            break
                        self.cap.release()
                    except:
                        continue
            else:
                self.cap = cv2.VideoCapture(camera_source)
            if not self.cap or not self.cap.isOpened():
                return False, f"Failed to open camera: {camera_source}"
            if camera_source == 0:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                self.cap.release()
                return False, f"Camera opened but cannot read frames from: {camera_source}"
            logging.info(f"Camera started successfully: {camera_source}")
            # Start threaded frame grabber
            self.stop_thread = False
            self.frame_thread = threading.Thread(target=self.threaded_frame_grabber, daemon=True)
            self.frame_thread.start()
            return True, f"Camera started successfully: {source_type}"
        except Exception as e:
            logging.error(f"Camera start error: {e}")
            if self.cap:
                self.cap.release()
            return False, f"Error starting camera: {str(e)}"

    def stop_camera(self):
        self.running = False
        self.stop_thread = True
        if self.frame_thread:
            self.frame_thread.join(timeout=1)
        if self.cap:
            self.cap.release()
        if self.out:
            self.out.release()
        self.status = False
        self.current_camera_source = None
        return "Camera stopped"

    def calculate_fps(self):
        self.fps_counter += 1
        if self.fps_counter % 10 == 0:
            current_time = time.time()
            self.current_fps = 10 / (current_time - self.fps_start_time)
            self.fps_start_time = current_time

    def process_frame(self):
        if not self.cap or not self.cap.isOpened():
            return None, {"Status": "Camera not initialized", "Error": "Please start camera first"}
        try:
            import torch
            model_device = str(next(self.yolo_model.model.parameters()).device) if self.yolo_model else 'unknown'
            cuda_available = torch.cuda.is_available()
            # Frame skipping
            for _ in range(self.frame_skip):
                with self.frame_lock:
                    frame = self.latest_frame.copy() if self.latest_frame is not None else None
                if frame is None:
                    return None, {"Status": "No frame available", "Error": "Waiting for camera..."}
                time.sleep(0.005)  # Lower sleep for higher FPS
            # Resize frame for inference (1080p)
            frame_resized = cv2.resize(frame, (self.resize_width, self.resize_height), interpolation=cv2.INTER_LINEAR)
            self.calculate_fps()
            detections, annotated_frame = self.detect_persons_yolo(frame_resized)
            # Optionally, upscale annotated_frame back to 1080p for display
            annotated_frame = cv2.resize(annotated_frame, (self.resize_width, self.resize_height), interpolation=cv2.INTER_LINEAR)
            tracked_frame, person_count = self.track_persons(detections, annotated_frame)
            person_detected = self.apply_smart_filtering(person_count)
            self.de.appendleft(person_detected)
            if sum(self.de) >= self.detection_thresh * 0.6 and not self.status:
                self.status = True
                self.entry_time = datetime.datetime.now().strftime("%A, %I-%M-%S %p %d %B %Y")
                try:
                    width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    if width <= 0 or height <= 0:
                        height, width = tracked_frame.shape[:2]
                    self.out = cv2.VideoWriter(
                        f'{self.output_dir}/{self.entry_time}.mp4',
                        cv2.VideoWriter_fourcc(*'mp4v'),
                        20.0,
                        (width, height)
                    )
                    logging.info(f"Started recording: {self.entry_time}")
                except Exception as e:
                    logging.error(f"Error initializing video writer: {e}")
            if self.status and not person_detected:
                if sum(self.de) > self.detection_thresh * 0.3:
                    if self.initial_time is None:
                        self.initial_time = time.time()
                elif self.initial_time is not None:
                    if time.time() - self.initial_time >= self.patience:
                        self.status = False
                        exit_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")
                        if self.out:
                            self.out.release()
                        self.initial_time = None
                        body = f"🚨 Security Alert:\n👤 Person Entered: {self.entry_time}\n🚪 Person Left: {exit_time}\n📹 Video saved to {self.output_dir}"
                        self.send_message(body)
                        logging.info(f"Person left at: {exit_time}")
            elif self.status and sum(self.de) > self.detection_thresh * 0.3:
                self.initial_time = None
            height, width = tracked_frame.shape[:2]
            current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
            current_day = datetime.datetime.now().strftime("%A")
            date = datetime.datetime.now().strftime("%d %B, %Y")
            overlay = tracked_frame.copy()
            cv2.rectangle(overlay, (5, 5), (400, 220), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, tracked_frame, 0.3, 0, tracked_frame)
            camera_display = "Laptop Camera" if self.current_camera_source == 0 else str(self.current_camera_source)
            info_texts = [
                f'🏠 Room Occupied: {self.status}',
                f'⏰ Time: {current_time}',
                f'📅 {current_day}, {date}',
                f'👥 Persons Detected: {person_count}',
                f'📊 Detection Score: {sum(self.de)}/{self.detection_thresh}',
                f'🎯 FPS: {self.current_fps:.1f}',
                f'📱 SMS: {"✅" if self.twilio_enabled else "❌"}',
                f'📹 Camera: {camera_display}',
                f'🖥️ Model Device: {model_device}',
                f'⚡ CUDA Available: {cuda_available}'
            ]
            y_offset = 25
            for text in info_texts:
                cv2.putText(tracked_frame, text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25
            if self.initial_time is not None:
                remaining_time = max(0, self.patience - (time.time() - self.initial_time))
                cv2.putText(tracked_frame, f'⏳ Leaving in: {remaining_time:.1f}s', (width - 250, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if self.status:
                cv2.circle(tracked_frame, (width - 30, 30), 10, (0, 0, 255), -1)
                cv2.putText(tracked_frame, 'REC', (width - 60, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            if self.status and self.out:
                try:
                    self.out.write(tracked_frame)
                except Exception as e:
                    logging.error(f"Error writing frame: {e}")
            tracked_frame_rgb = cv2.cvtColor(tracked_frame, cv2.COLOR_BGR2RGB)
            if person_detected:
                self.detection_count += 1
            status_info = {
                "🏠 Room Occupied": self.status,
                "👥 Current Persons": person_count,
                "📊 Detection Score": f"{sum(self.de)}/{self.detection_thresh}",
                "📈 Total Detections": self.detection_count,
                "📹 Recording": self.status,
                "🎯 FPS": round(self.current_fps, 1),
                "📱 SMS Alerts": self.twilio_enabled,
                "🔧 Model": "YOLOv8",
                "🖥️ Model Device": model_device,
                "⚡ CUDA Available": cuda_available,
                "⚡ Confidence": self.confidence_threshold,
                "🎚️ Area Threshold": self.area_threshold,
                "📷 Camera Source": camera_display,
                "✅ Status": "Running"
            }
            if not cuda_available or model_device == 'cpu':
                logging.warning("YOLOv8 is running on CPU! Performance will be low. Check your CUDA installation and PyTorch/Ultralytics setup.")
            return tracked_frame_rgb, status_info
        except Exception as e:
            logging.error(f"Frame processing error: {e}")
            return None, {"Status": "Processing error", "Error": str(e)}

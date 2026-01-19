"""
Camera Handler Module
Handles single camera with frame splitting, virtual line detection, and number plate recognition
"""

import cv2
import pytesseract
import numpy as np
import logging
import threading
import time
from typing import Optional, Tuple, Callable
from enum import Enum

from config_manager import ConfigManager

logger = logging.getLogger(__name__)


class Zone(Enum):
    """Camera frame zones"""
    ENTRY = "entry"
    EXIT = "exit"


class CameraHandler:
    """Handles camera operations with frame splitting and virtual line detection"""
    
    def __init__(self, camera_index=0, use_config=True):
        """
        Initialize camera handler
        
        Args:
            camera_index: USB camera index (default: 0)
            use_config: Whether to load zone configuration from file (default: True)
        """
        self.camera_index = camera_index
        self.use_config = use_config
        
        # Load configuration
        self.config_manager = ConfigManager()
        if use_config:
            config = self.config_manager.load_config()
            self.entry_zone = config["entry_zone"]
            self.exit_zone = config["exit_zone"]
            self.entry_virtual_line_position = config.get("entry_virtual_line_position", 0.5)
            self.exit_virtual_line_position = config.get("exit_virtual_line_position", 0.5)
            self.motion_threshold = config.get("motion_threshold", 500)
            self.frame_width = config.get("frame_width", 1280)
            self.frame_height = config.get("frame_height", 720)
        else:
            # Use defaults
            self.entry_zone = {"x1": 0, "y1": 0, "x2": 640, "y2": 480}
            self.exit_zone = {"x1": 640, "y1": 0, "x2": 1280, "y2": 480}
            self.entry_virtual_line_position = 0.5
            self.exit_virtual_line_position = 0.5
            self.motion_threshold = 500
            self.frame_width = 1280
            self.frame_height = 720
        
        self.camera = None
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        
        # Calculate virtual line positions (will be updated when camera is initialized)
        self.entry_virtual_line_y = None
        self.exit_virtual_line_y = None
        
        # Callbacks for virtual line crossings
        self.entry_callback: Optional[Callable] = None
        self.exit_callback: Optional[Callable] = None
        
        # Processing state
        self.processing = False
        self.processing_thread = None
        self.last_entry_crossing_time = 0
        self.last_exit_crossing_time = 0
        self.crossing_cooldown = 3.0  # Seconds between crossing detections
        
    def initialize_camera(self):
        """Initialize camera"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                raise Exception(f"Failed to open camera at index {self.camera_index}")
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            
            logger.info(f"Camera initialized at index {self.camera_index}")
            
            # Get actual frame dimensions (may differ from requested)
            ret, test_frame = self.camera.read()
            if ret:
                actual_height, actual_width = test_frame.shape[:2]
                # Scale virtual line positions based on actual frame height
                self.entry_virtual_line_y = int(actual_height * self.entry_virtual_line_position)
                self.exit_virtual_line_y = int(actual_height * self.exit_virtual_line_position)
                logger.info(f"Frame dimensions: {actual_width}x{actual_height}")
                logger.info(f"Entry zone: ({self.entry_zone['x1']}, {self.entry_zone['y1']}) to ({self.entry_zone['x2']}, {self.entry_zone['y2']})")
                logger.info(f"Exit zone: ({self.exit_zone['x1']}, {self.exit_zone['y1']}) to ({self.exit_zone['x2']}, {self.exit_zone['y2']})")
                logger.info(f"Entry virtual line at y={self.entry_virtual_line_y} (ratio={self.entry_virtual_line_position})")
                logger.info(f"Exit virtual line at y={self.exit_virtual_line_y} (ratio={self.exit_virtual_line_position})")
            
            # Allow camera to stabilize and learn background
            logger.info("Learning background (5 seconds)...")
            for _ in range(150):  # ~5 seconds at 30fps
                ret, frame = self.camera.read()
                if ret:
                    self.background_subtractor.apply(frame)
            logger.info("Background learning complete")
            
            return True
            
        except Exception as e:
            logger.error(f"Camera initialization error: {e}")
            return False
    
    def start_processing(self, entry_callback: Optional[Callable] = None,
                        exit_callback: Optional[Callable] = None):
        """
        Start continuous frame processing with virtual line detection
        
        Args:
            entry_callback: Function to call when entry virtual line is crossed
                          Callback receives (frame, zone_image) as arguments
            exit_callback: Function to call when exit virtual line is crossed
                          Callback receives (frame, zone_image) as arguments
        """
        if self.camera is None or not self.camera.isOpened():
            logger.error("Camera not initialized")
            return False
        
        self.entry_callback = entry_callback
        self.exit_callback = exit_callback
        self.processing = True
        
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)
        self.processing_thread.start()
        
        logger.info("Frame processing started")
        return True
    
    def stop_processing(self):
        """Stop continuous frame processing"""
        self.processing = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        logger.info("Frame processing stopped")
    
    def _process_frames(self):
        """Main frame processing loop with virtual line detection"""
        while self.processing:
            ret, frame = self.camera.read()
            if not ret:
                logger.warning("Failed to read frame")
                time.sleep(0.1)
                continue
            
            # Apply background subtraction
            fg_mask = self.background_subtractor.apply(frame)
            
            # Process entry zone
            self._check_virtual_line_crossing(
                frame, fg_mask, Zone.ENTRY, self.entry_callback
            )
            
            # Process exit zone
            self._check_virtual_line_crossing(
                frame, fg_mask, Zone.EXIT, self.exit_callback
            )
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.033)  # ~30 FPS
    
    def _check_virtual_line_crossing(self, frame: np.ndarray, fg_mask: np.ndarray,
                                    zone: Zone, callback: Optional[Callable]):
        """
        Check if vehicle crosses virtual line in specified zone
        
        Args:
            frame: Full camera frame
            fg_mask: Foreground mask from background subtraction
            zone: Zone to check (ENTRY or EXIT)
            callback: Callback function if crossing detected
        """
        current_time = time.time()
        
        # Extract zone from frame using configured coordinates
        if zone == Zone.ENTRY:
            x1, y1 = self.entry_zone["x1"], self.entry_zone["y1"]
            x2, y2 = self.entry_zone["x2"], self.entry_zone["y2"]
            zone_frame = frame[y1:y2, x1:x2]
            zone_mask = fg_mask[y1:y2, x1:x2]
            virtual_line_y = self.entry_virtual_line_y
            last_crossing_time = self.last_entry_crossing_time
            # Adjust virtual line relative to zone
            zone_virtual_line_y = virtual_line_y - y1
        else:  # EXIT
            x1, y1 = self.exit_zone["x1"], self.exit_zone["y1"]
            x2, y2 = self.exit_zone["x2"], self.exit_zone["y2"]
            zone_frame = frame[y1:y2, x1:x2]
            zone_mask = fg_mask[y1:y2, x1:x2]
            virtual_line_y = self.exit_virtual_line_y
            last_crossing_time = self.last_exit_crossing_time
            # Adjust virtual line relative to zone
            zone_virtual_line_y = virtual_line_y - y1
        
        # Check cooldown period
        if current_time - last_crossing_time < self.crossing_cooldown:
            return
        
        # Find contours in the zone
        contours, _ = cv2.findContours(
            zone_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Check if any contour crosses the virtual line
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.motion_threshold:
                continue
            
            # Get bounding box
            _, y, _, h = cv2.boundingRect(contour)
            contour_bottom = y + h
            contour_top = y
            
            # Check if contour crosses virtual line (from above or below)
            # Use zone-relative virtual line position
            if (contour_top <= zone_virtual_line_y <= contour_bottom):
                # Vehicle detected crossing virtual line
                logger.info(f"Vehicle detected crossing {zone.value} virtual line")
                
                if zone == Zone.ENTRY:
                    self.last_entry_crossing_time = current_time
                else:
                    self.last_exit_crossing_time = current_time
                
                # Call callback if provided
                if callback:
                    try:
                        callback(frame.copy(), zone_frame.copy())
                    except Exception as e:
                        logger.error(f"Error in {zone.value} callback: {e}")
                
                break
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture current frame from camera
        
        Returns:
            numpy.ndarray: Captured frame, or None if failed
        """
        if self.camera is None or not self.camera.isOpened():
            logger.error("Camera not initialized")
            return None
        
        try:
            ret, frame = self.camera.read()
            if ret:
                return frame
            return None
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def extract_zone(self, frame: np.ndarray, zone: Zone) -> Optional[np.ndarray]:
        """
        Extract zone from full frame
        
        Args:
            frame: Full camera frame
            zone: Zone to extract (ENTRY or EXIT)
        
        Returns:
            numpy.ndarray: Zone frame, or None if failed
        """
        if frame is None:
            return None
        
        try:
            if zone == Zone.ENTRY:
                x1, y1 = self.entry_zone["x1"], self.entry_zone["y1"]
                x2, y2 = self.entry_zone["x2"], self.entry_zone["y2"]
                return frame[y1:y2, x1:x2]
            else:  # EXIT
                x1, y1 = self.exit_zone["x1"], self.exit_zone["y1"]
                x2, y2 = self.exit_zone["x2"], self.exit_zone["y2"]
                return frame[y1:y2, x1:x2]
        except Exception as e:
            logger.error(f"Error extracting {zone.value} zone: {e}")
            return None
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image: Input image
        
        Returns:
            numpy.ndarray: Preprocessed image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def extract_number_plate(self, image: np.ndarray) -> Optional[str]:
        """
        Extract number plate text from image using Tesseract OCR
        
        Args:
            image: Input image containing number plate
        
        Returns:
            str: Extracted number plate text, or None if extraction failed
        """
        if image is None:
            return None
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Configure Tesseract for number plate recognition
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Clean up the extracted text
            cleaned_text = self._clean_number_plate_text(text)
            
            if cleaned_text:
                logger.info(f"Extracted number plate: {cleaned_text}")
                return cleaned_text
            else:
                logger.warning("No number plate text extracted")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting number plate: {e}")
            return None
    
    def _clean_number_plate_text(self, text: str) -> str:
        """
        Clean and validate number plate text
        
        Args:
            text: Raw OCR text
        
        Returns:
            str: Cleaned number plate text
        """
        # Remove whitespace and special characters
        cleaned = ''.join(c for c in text.upper() if c.isalnum())
        
        # Basic validation: number plate should have reasonable length (3-10 characters)
        if len(cleaned) < 3 or len(cleaned) > 10:
            return ""
        
        return cleaned
    
    def extract_number_plate_from_zone(self, frame: np.ndarray, zone: Zone) -> Optional[str]:
        """
        Extract number plate from specific zone of frame
        
        Args:
            frame: Full camera frame
            zone: Zone to extract from (ENTRY or EXIT)
        
        Returns:
            str: Extracted number plate, or None if failed
        """
        zone_image = self.extract_zone(frame, zone)
        if zone_image is None:
            return None
        return self.extract_number_plate(zone_image)
    
    def release_camera(self):
        """Release camera resources"""
        self.stop_processing()
        
        if self.camera is not None:
            self.camera.release()
            logger.info("Camera released")
    
    def __del__(self):
        """Destructor to ensure camera is released"""
        self.release_camera()

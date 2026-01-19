#!/usr/bin/env python3
"""
Zone Configuration Tool
Interactive tool to configure entry/exit zones and virtual line position
"""

import cv2
import numpy as np
import sys
import os
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager


class ZoneConfigurator:
    """Interactive zone configuration tool"""
    
    def __init__(self, camera_index=0):
        """
        Initialize zone configurator
        
        Args:
            camera_index: USB camera index
        """
        self.camera_index = camera_index
        self.camera = None
        self.config_manager = ConfigManager()
        
        # Zone selection state
        self.entry_points = []  # [top_left, bottom_right]
        self.exit_points = []   # [top_left, bottom_right]
        self.entry_virtual_line_y = None
        self.exit_virtual_line_y = None
        
        # Current selection mode
        self.mode = "entry"  # "entry", "exit", "entry_virtual_line", "exit_virtual_line"
        self.current_point = None
        
        # Window name
        self.window_name = "Zone Configuration - Click to set zones"
        
    def initialize_camera(self):
        """Initialize camera"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                raise Exception(f"Failed to open camera at index {self.camera_index}")
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            print("Camera initialized successfully")
            return True
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
    
    def mouse_callback(self, event, x, y, flags, param):
        """
        Mouse callback for zone selection
        
        Args:
            event: OpenCV mouse event
            x, y: Mouse coordinates
            flags: Event flags
            param: User data
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.mode == "entry":
                if len(self.entry_points) == 0:
                    # First point (top-left)
                    self.entry_points = [(x, y)]
                    print(f"Entry zone - Point 1 (top-left): ({x}, {y})")
                elif len(self.entry_points) == 1:
                    # Second point (bottom-right)
                    self.entry_points.append((x, y))
                    print(f"Entry zone - Point 2 (bottom-right): ({x}, {y})")
                    print("Entry zone configured! Press 'e' to configure exit zone.")
            
            elif self.mode == "exit":
                if len(self.exit_points) == 0:
                    # First point (top-left)
                    self.exit_points = [(x, y)]
                    print(f"Exit zone - Point 1 (top-left): ({x}, {y})")
                elif len(self.exit_points) == 1:
                    # Second point (bottom-right)
                    self.exit_points.append((x, y))
                    print(f"Exit zone - Point 2 (bottom-right): ({x}, {y})")
                    print("Exit zone configured! Press 'v' to set entry virtual line.")
            
            elif self.mode == "entry_virtual_line":
                # Set entry virtual line position (y coordinate)
                self.entry_virtual_line_y = y
                print(f"Entry virtual line set at y={y}")
                print("Entry virtual line configured! Press 'x' to set exit virtual line.")
            
            elif self.mode == "exit_virtual_line":
                # Set exit virtual line position (y coordinate)
                self.exit_virtual_line_y = y
                print(f"Exit virtual line set at y={y}")
                print("Configuration complete! Press 's' to save.")
    
    def draw_zones(self, frame):
        """
        Draw configured zones on frame
        
        Args:
            frame: Camera frame
        
        Returns:
            numpy.ndarray: Frame with zones drawn
        """
        display_frame = frame.copy()
        
        # Draw entry zone
        if len(self.entry_points) == 2:
            x1, y1 = self.entry_points[0]
            x2, y2 = self.entry_points[1]
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, "ENTRY ZONE", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        elif len(self.entry_points) == 1:
            x, y = self.entry_points[0]
            cv2.circle(display_frame, (x, y), 5, (0, 255, 0), -1)
            cv2.putText(display_frame, "Click for bottom-right", (x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Draw exit zone
        if len(self.exit_points) == 2:
            x1, y1 = self.exit_points[0]
            x2, y2 = self.exit_points[1]
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(display_frame, "EXIT ZONE", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        elif len(self.exit_points) == 1:
            x, y = self.exit_points[0]
            cv2.circle(display_frame, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(display_frame, "Click for bottom-right", (x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Draw entry virtual line
        if self.entry_virtual_line_y is not None:
            h, w = display_frame.shape[:2]
            # Only draw in entry zone if zone is configured
            if len(self.entry_points) == 2:
                x1, y1 = self.entry_points[0]
                x2, y2 = self.entry_points[1]
                x_min = min(x1, x2)
                x_max = max(x1, x2)
                cv2.line(display_frame, (x_min, self.entry_virtual_line_y), 
                        (x_max, self.entry_virtual_line_y), (255, 255, 0), 2)
                cv2.putText(display_frame, "ENTRY VIRTUAL LINE", (x_min + 10, self.entry_virtual_line_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Draw exit virtual line
        if self.exit_virtual_line_y is not None:
            h, w = display_frame.shape[:2]
            # Only draw in exit zone if zone is configured
            if len(self.exit_points) == 2:
                x1, y1 = self.exit_points[0]
                x2, y2 = self.exit_points[1]
                x_min = min(x1, x2)
                x_max = max(x1, x2)
                cv2.line(display_frame, (x_min, self.exit_virtual_line_y), 
                        (x_max, self.exit_virtual_line_y), (255, 165, 0), 2)
                cv2.putText(display_frame, "EXIT VIRTUAL LINE", (x_min + 10, self.exit_virtual_line_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
        
        # Draw instructions
        instructions = []
        if self.mode == "entry":
            if len(self.entry_points) == 0:
                instructions.append("Mode: ENTRY ZONE - Click top-left corner")
            elif len(self.entry_points) == 1:
                instructions.append("Mode: ENTRY ZONE - Click bottom-right corner")
        elif self.mode == "exit":
            if len(self.exit_points) == 0:
                instructions.append("Mode: EXIT ZONE - Click top-left corner")
            elif len(self.exit_points) == 1:
                instructions.append("Mode: EXIT ZONE - Click bottom-right corner")
        elif self.mode == "entry_virtual_line":
            instructions.append("Mode: ENTRY VIRTUAL LINE - Click to set line position")
        elif self.mode == "exit_virtual_line":
            instructions.append("Mode: EXIT VIRTUAL LINE - Click to set line position")
        
        instructions.append("Press 'e' for exit zone, 'v' for entry virtual line, 'x' for exit virtual line")
        instructions.append("Press 's' to save, 'q' to quit")
        instructions.append("Press 'r' to reset current zone")
        
        y_offset = 30
        for i, instruction in enumerate(instructions):
            cv2.putText(display_frame, instruction, (10, y_offset + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return display_frame
    
    def save_configuration(self) -> bool:
        """
        Save current configuration
        
        Returns:
            bool: True if successful, False otherwise
        """
        if len(self.entry_points) != 2 or len(self.exit_points) != 2:
            print("Error: Both entry and exit zones must be configured")
            return False
        
        if self.entry_virtual_line_y is None or self.exit_virtual_line_y is None:
            print("Error: Both entry and exit virtual line positions must be set")
            return False
        
        # Get frame dimensions
        ret, frame = self.camera.read()
        if not ret:
            print("Error: Could not read frame to get dimensions")
            return False
        
        h, w = frame.shape[:2]
        
        # Calculate virtual line positions as ratios
        entry_virtual_line_ratio = self.entry_virtual_line_y / h
        exit_virtual_line_ratio = self.exit_virtual_line_y / h
        
        # Create configuration
        config = {
            "entry_zone": {
                "x1": min(self.entry_points[0][0], self.entry_points[1][0]),
                "y1": min(self.entry_points[0][1], self.entry_points[1][1]),
                "x2": max(self.entry_points[0][0], self.entry_points[1][0]),
                "y2": max(self.entry_points[0][1], self.entry_points[1][1])
            },
            "exit_zone": {
                "x1": min(self.exit_points[0][0], self.exit_points[1][0]),
                "y1": min(self.exit_points[0][1], self.exit_points[1][1]),
                "x2": max(self.exit_points[0][0], self.exit_points[1][0]),
                "y2": max(self.exit_points[0][1], self.exit_points[1][1])
            },
            "entry_virtual_line_position": entry_virtual_line_ratio,
            "exit_virtual_line_position": exit_virtual_line_ratio,
            "frame_width": w,
            "frame_height": h,
            "motion_threshold": 500
        }
        
        # Save configuration
        if self.config_manager.save_config(config):
            print("Configuration saved successfully!")
            print(f"Entry zone: ({config['entry_zone']['x1']}, {config['entry_zone']['y1']}) to ({config['entry_zone']['x2']}, {config['entry_zone']['y2']})")
            print(f"Exit zone: ({config['exit_zone']['x1']}, {config['exit_zone']['y1']}) to ({config['exit_zone']['x2']}, {config['exit_zone']['y2']})")
            print(f"Entry virtual line position: {entry_virtual_line_ratio:.2f} ({self.entry_virtual_line_y} pixels)")
            print(f"Exit virtual line position: {exit_virtual_line_ratio:.2f} ({self.exit_virtual_line_y} pixels)")
            return True
        else:
            print("Error: Failed to save configuration")
            return False
    
    def reset_current_zone(self):
        """Reset current zone selection"""
        if self.mode == "entry":
            self.entry_points = []
            print("Entry zone reset")
        elif self.mode == "exit":
            self.exit_points = []
            print("Exit zone reset")
        elif self.mode == "entry_virtual_line":
            self.entry_virtual_line_y = None
            print("Entry virtual line reset")
        elif self.mode == "exit_virtual_line":
            self.exit_virtual_line_y = None
            print("Exit virtual line reset")
    
    def run(self):
        """Run configuration tool"""
        if not self.initialize_camera():
            return False
        
        # Create window and set mouse callback
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print("\n" + "="*60)
        print("Zone Configuration Tool")
        print("="*60)
        print("Instructions:")
        print("1. Click two points to define ENTRY ZONE (top-left, then bottom-right)")
        print("2. Press 'e' to switch to EXIT ZONE configuration")
        print("3. Click two points to define EXIT ZONE")
        print("4. Press 'v' to set ENTRY VIRTUAL LINE position")
        print("5. Click to set entry virtual line y-position")
        print("6. Press 'x' to set EXIT VIRTUAL LINE position")
        print("7. Click to set exit virtual line y-position")
        print("8. Press 's' to save configuration")
        print("9. Press 'q' to quit without saving")
        print("10. Press 'r' to reset current zone")
        print("="*60 + "\n")
        
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    print("Error: Failed to read frame")
                    break
                
                # Draw zones on frame
                display_frame = self.draw_zones(frame)
                
                # Show frame
                cv2.imshow(self.window_name, display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("Quitting without saving...")
                    break
                elif key == ord('e'):
                    if len(self.entry_points) == 2:
                        self.mode = "exit"
                        print("Switched to EXIT ZONE configuration")
                    else:
                        print("Please complete ENTRY ZONE configuration first")
                elif key == ord('v'):
                    if len(self.entry_points) == 2 and len(self.exit_points) == 2:
                        self.mode = "entry_virtual_line"
                        print("Switched to ENTRY VIRTUAL LINE configuration")
                    else:
                        print("Please complete both ENTRY and EXIT ZONE configurations first")
                elif key == ord('x'):
                    if len(self.exit_points) == 2 and self.entry_virtual_line_y is not None:
                        self.mode = "exit_virtual_line"
                        print("Switched to EXIT VIRTUAL LINE configuration")
                    else:
                        print("Please complete ENTRY VIRTUAL LINE configuration first")
                elif key == ord('s'):
                    if self.save_configuration():
                        print("Press 'q' to exit")
                    else:
                        print("Configuration not saved. Please complete all steps.")
                elif key == ord('r'):
                    self.reset_current_zone()
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            # Cleanup
            self.camera.release()
            cv2.destroyAllWindows()
            print("Configuration tool closed")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Zone Configuration Tool')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera index (default: 0)')
    
    args = parser.parse_args()
    
    configurator = ZoneConfigurator(camera_index=args.camera)
    configurator.run()


if __name__ == "__main__":
    main()


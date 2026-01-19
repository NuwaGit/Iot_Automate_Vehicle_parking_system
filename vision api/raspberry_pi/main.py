#!/usr/bin/env python3
"""
Parking System - Main Controller (Simplified)
Main event loop with virtual line detection coordinating all components
"""

import sys
import os
import time
import logging
import threading
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from serial_comm import SerialCommunicator, open_entry_gate, close_entry_gate, open_exit_gate, close_exit_gate, buzzer_on, buzzer_off
from camera_handler import CameraHandler, Zone
from fee_calculator import FeeCalculator
from data_manager import DataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parking_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ParkingSystem:
    """Main parking system controller"""
    
    def __init__(self, serial_port=None, camera_index=0, hourly_rate=10.0, total_slots=1,
                 use_config=True, credentials_path=None):
        """
        Initialize parking system
        
        Args:
            serial_port: Serial port for ESP32 communication (None for auto-detect)
            camera_index: USB camera index (default: 0)
            hourly_rate: Parking fee per hour in dollars
            total_slots: Total number of parking slots (default: 1)
            use_config: Whether to load zone configuration from file (default: True)
            credentials_path: Path to Google Cloud credentials JSON file (optional)
        """
        self.total_slots = total_slots
        self.hourly_rate = hourly_rate
        
        # Initialize components
        logger.info("Initializing parking system components...")
        
        self.serial_comm = SerialCommunicator(port=serial_port)
        self.camera_handler = CameraHandler(
            camera_index=camera_index,
            use_config=use_config
        )
        self.fee_calculator = FeeCalculator(hourly_rate)
        self.data_manager = DataManager()
        
        # System state
        self.running = False
        self.entry_gate_processing = False
        self.exit_gate_processing = False
        self.slot_occupied = False  # Track slot status from ESP32
        
        # Lock for thread-safe operations
        self.processing_lock = threading.Lock()
        
        logger.info("Parking system initialized")
    
    def start(self):
        """Start the parking system"""
        logger.info("Starting parking system...")
        
        # Connect to ESP32
        if not self.serial_comm.connect():
            logger.error("Failed to connect to ESP32. Please check connections.")
            return False
        
        # Initialize camera
        if not self.camera_handler.initialize_camera():
            logger.error("Failed to initialize camera. Please check camera connection.")
            return False
        
        # Start camera processing with virtual line detection callbacks
        if not self.camera_handler.start_processing(
            entry_callback=self._handle_entry_virtual_line,
            exit_callback=self._handle_exit_virtual_line
        ):
            logger.error("Failed to start camera processing.")
            return False
        
        self.running = True
        logger.info("Parking system started successfully")
        
        # Main event loop
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the parking system"""
        logger.info("Stopping parking system...")
        self.running = False
        
        # Stop camera processing
        self.camera_handler.stop_processing()
        
        # Close gates
        close_entry_gate(self.serial_comm)
        close_exit_gate(self.serial_comm)
        buzzer_off(self.serial_comm)
        
        # Release resources
        self.camera_handler.release_camera()
        self.serial_comm.disconnect()
        
        logger.info("Parking system stopped")
    
    def _main_loop(self):
        """Main event processing loop"""
        logger.info("Entering main event loop...")
        
        while self.running:
            # Read messages from ESP32 (parking slot status)
            messages = self.serial_comm.read_all_messages()
            
            for message in messages:
                self._handle_message(message)
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)
    
    def _handle_message(self, message: str):
        """
        Handle message from ESP32
        
        Args:
            message: Message string from ESP32
        """
        logger.debug(f"Handling message: {message}")
        
        if message == "SLOT_OCCUPIED":
            self.slot_occupied = True
            logger.info("Parking slot is now occupied")
        elif message == "SLOT_FREE":
            self.slot_occupied = False
            logger.info("Parking slot is now free")
        else:
            logger.warning(f"Unknown message: {message}")
    
    def _handle_entry_virtual_line(self, frame, zone_image):
        """
        Handle vehicle crossing entry virtual line
        
        Args:
            frame: Full camera frame
            zone_image: Entry zone image
        """
        with self.processing_lock:
            if self.entry_gate_processing:
                logger.warning("Entry gate already processing, ignoring virtual line trigger")
                return
            
            logger.info("Vehicle detected crossing entry virtual line")
            self.entry_gate_processing = True
        
        # Check if parking is full
        if self.data_manager.is_parking_full(self.total_slots) or self.slot_occupied:
            logger.warning("Parking is full! Activating buzzer...")
            buzzer_on(self.serial_comm)
            # Turn off buzzer after 3 seconds
            time.sleep(3)
            buzzer_off(self.serial_comm)
            with self.processing_lock:
                self.entry_gate_processing = False
            return
        
        # Extract number plate from entry zone
        logger.info("Extracting number plate from entry zone...")
        number_plate = self.camera_handler.extract_number_plate(zone_image)
        
        if not number_plate:
            logger.warning("Failed to extract number plate. Retrying...")
            # Retry with full frame entry zone
            time.sleep(0.5)
            number_plate = self.camera_handler.extract_number_plate_from_zone(frame, Zone.ENTRY)
        
        if not number_plate:
            logger.error("Failed to extract number plate after retry. Entry denied.")
            with self.processing_lock:
                self.entry_gate_processing = False
            return
        
        logger.info(f"Number plate extracted: {number_plate}")
        
        # Check if vehicle is already in system
        existing_vehicle = self.data_manager.get_vehicle_entry(number_plate)
        if existing_vehicle:
            logger.warning(f"Vehicle {number_plate} is already in the system!")
            with self.processing_lock:
                self.entry_gate_processing = False
            return
        
        # Get available slot (should be slot 1)
        available_slots = self.data_manager.get_available_slots(self.total_slots)
        if not available_slots:
            logger.error("No available slots (race condition?)")
            with self.processing_lock:
                self.entry_gate_processing = False
            return
        
        slot = available_slots[0]
        
        # Add vehicle entry record
        entry_time = datetime.now()
        if self.data_manager.add_vehicle_entry(number_plate, entry_time, slot):
            logger.info(f"Vehicle {number_plate} entered at {entry_time}, assigned to slot {slot}")
            
            # Open entry gate
            open_entry_gate(self.serial_comm)
            
            # Close gate after timeout (vehicle should pass through)
            # In a real system, you might want to detect when vehicle passes
            threading.Timer(5.0, self._close_entry_gate_after_timeout).start()
        else:
            logger.error("Failed to add vehicle entry record")
            with self.processing_lock:
                self.entry_gate_processing = False
    
    def _close_entry_gate_after_timeout(self):
        """Close entry gate after timeout"""
        with self.processing_lock:
            if self.entry_gate_processing:
                close_entry_gate(self.serial_comm)
                self.entry_gate_processing = False
                logger.info("Entry gate closed after timeout")
    
    def _handle_exit_virtual_line(self, frame, zone_image):
        """
        Handle vehicle crossing exit virtual line
        
        Args:
            frame: Full camera frame
            zone_image: Exit zone image
        """
        with self.processing_lock:
            if self.exit_gate_processing:
                logger.warning("Exit gate already processing, ignoring virtual line trigger")
                return
            
            logger.info("Vehicle detected crossing exit virtual line")
            self.exit_gate_processing = True
        
        # Extract number plate from exit zone
        logger.info("Extracting number plate from exit zone...")
        number_plate = self.camera_handler.extract_number_plate(zone_image)
        
        if not number_plate:
            logger.warning("Failed to extract number plate. Retrying...")
            # Retry with full frame exit zone
            time.sleep(0.5)
            number_plate = self.camera_handler.extract_number_plate_from_zone(frame, Zone.EXIT)
        
        if not number_plate:
            logger.error("Failed to extract number plate after retry.")
            with self.processing_lock:
                self.exit_gate_processing = False
            return
        
        logger.info(f"Number plate extracted: {number_plate}")
        
        # Get vehicle entry record
        vehicle_entry = self.data_manager.get_vehicle_entry(number_plate)
        
        if not vehicle_entry:
            logger.warning(f"Vehicle {number_plate} not found in system. Entry may have failed.")
            with self.processing_lock:
                self.exit_gate_processing = False
            return
        
        # Calculate fee
        entry_time = vehicle_entry["entry_time"]
        exit_time = datetime.now()
        fee = self.fee_calculator.calculate_fee(entry_time, exit_time)
        duration_str = self.fee_calculator.calculate_duration_string(entry_time, exit_time)
        
        logger.info(f"Vehicle {number_plate} - Duration: {duration_str}, Fee: {self.fee_calculator.format_fee(fee)}")
        
        # Print fee information
        print("\n" + "="*50)
        print("Parking Fee Receipt")
        print("="*50)
        print(f"Number Plate: {number_plate}")
        print(f"Entry Time: {entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Exit Time: {exit_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration_str}")
        print(f"Fee: {self.fee_calculator.format_fee(fee)}")
        print("="*50 + "\n")
        
        # Add to history
        slot = vehicle_entry["slot"]
        self.data_manager.add_history_record(number_plate, entry_time, exit_time, fee, slot)
        
        # Remove from active vehicles
        self.data_manager.remove_vehicle_entry(number_plate)
        
        logger.info(f"Vehicle {number_plate} removed from active records")
        
        # Open exit gate
        open_exit_gate(self.serial_comm)
        
        # Close gate after timeout
        threading.Timer(5.0, self._close_exit_gate_after_timeout).start()
    
    def _close_exit_gate_after_timeout(self):
        """Close exit gate after timeout"""
        with self.processing_lock:
            if self.exit_gate_processing:
                close_exit_gate(self.serial_comm)
                self.exit_gate_processing = False
                logger.info("Exit gate closed after timeout")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parking System Controller (Simplified)')
    parser.add_argument('--serial-port', type=str, default=None,
                        help='Serial port for ESP32 (auto-detect if not specified)')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera index (default: 0)')
    parser.add_argument('--hourly-rate', type=float, default=10.0,
                        help='Parking fee per hour in dollars (default: 10.0)')
    parser.add_argument('--slots', type=int, default=1,
                        help='Total number of parking slots (default: 1)')
    parser.add_argument('--no-config', action='store_true',
                        help='Do not load zone configuration from file (use defaults)')
    parser.add_argument('--credentials', type=str, default=None,
                        help='Path to Google Cloud credentials JSON file (optional)')
    
    args = parser.parse_args()
    
    # Create and start parking system
    system = ParkingSystem(
        serial_port=args.serial_port,
        camera_index=args.camera,
        hourly_rate=args.hourly_rate,
        total_slots=args.slots,
        use_config=not args.no_config,
        credentials_path=args.credentials
    )
    
    system.start()


if __name__ == "__main__":
    main()

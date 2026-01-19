"""
Data Manager Module
Handles JSON file operations for vehicle records and parking history
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class DataManager:
    """Manages parking data storage in JSON files"""
    
    def __init__(self, data_dir="data", vehicles_file="vehicles.json", history_file="history.json"):
        """
        Initialize data manager
        
        Args:
            data_dir: Directory path for data files
            vehicles_file: Filename for active vehicles
            history_file: Filename for parking history
        """
        self.data_dir = data_dir
        self.vehicles_file = os.path.join(data_dir, vehicles_file)
        self.history_file = os.path.join(data_dir, history_file)
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize files if they don't exist
        self._initialize_files()
    
    def _initialize_files(self):
        """Initialize JSON files if they don't exist"""
        if not os.path.exists(self.vehicles_file):
            self._write_json(self.vehicles_file, {"vehicles": []})
            logger.info(f"Initialized {self.vehicles_file}")
        
        if not os.path.exists(self.history_file):
            self._write_json(self.history_file, {"history": []})
            logger.info(f"Initialized {self.history_file}")
    
    def _read_json(self, filepath: str) -> dict:
        """Read JSON file"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            return {}
    
    def _write_json(self, filepath: str, data: dict):
        """Write JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error writing to {filepath}: {e}")
    
    def add_vehicle_entry(self, number_plate: str, entry_time: datetime, slot: int = 1) -> bool:
        """
        Add vehicle entry record
        
        Args:
            number_plate: Vehicle number plate
            entry_time: Entry timestamp
            slot: Parking slot number (default: 1, only one slot available)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = self._read_json(self.vehicles_file)
            vehicles = data.get("vehicles", [])
            
            # Check if vehicle already exists (shouldn't happen, but safety check)
            for vehicle in vehicles:
                if vehicle.get("number_plate") == number_plate:
                    logger.warning(f"Vehicle {number_plate} already in system")
                    return False
            
            # Add new vehicle entry
            vehicle_entry = {
                "number_plate": number_plate,
                "entry_time": entry_time.isoformat(),
                "slot": slot
            }
            
            vehicles.append(vehicle_entry)
            data["vehicles"] = vehicles
            self._write_json(self.vehicles_file, data)
            
            logger.info(f"Added vehicle entry: {number_plate} at slot {slot}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding vehicle entry: {e}")
            return False
    
    def get_vehicle_entry(self, number_plate: str) -> Optional[Dict]:
        """
        Get vehicle entry record by number plate
        
        Args:
            number_plate: Vehicle number plate
        
        Returns:
            dict: Vehicle entry record, or None if not found
        """
        try:
            data = self._read_json(self.vehicles_file)
            vehicles = data.get("vehicles", [])
            
            for vehicle in vehicles:
                if vehicle.get("number_plate") == number_plate:
                    # Convert ISO format string back to datetime
                    entry_time_str = vehicle.get("entry_time")
                    vehicle_copy = vehicle.copy()
                    vehicle_copy["entry_time"] = datetime.fromisoformat(entry_time_str)
                    return vehicle_copy
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting vehicle entry: {e}")
            return None
    
    def remove_vehicle_entry(self, number_plate: str) -> bool:
        """
        Remove vehicle entry record
        
        Args:
            number_plate: Vehicle number plate
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = self._read_json(self.vehicles_file)
            vehicles = data.get("vehicles", [])
            
            # Find and remove vehicle
            original_count = len(vehicles)
            vehicles = [v for v in vehicles if v.get("number_plate") != number_plate]
            
            if len(vehicles) < original_count:
                data["vehicles"] = vehicles
                self._write_json(self.vehicles_file, data)
                logger.info(f"Removed vehicle entry: {number_plate}")
                return True
            else:
                logger.warning(f"Vehicle {number_plate} not found in active records")
                return False
                
        except Exception as e:
            logger.error(f"Error removing vehicle entry: {e}")
            return False
    
    def add_history_record(self, number_plate: str, entry_time: datetime, 
                          exit_time: datetime, fee: float, slot: int) -> bool:
        """
        Add parking history record
        
        Args:
            number_plate: Vehicle number plate
            entry_time: Entry timestamp
            exit_time: Exit timestamp
            fee: Parking fee charged
            slot: Parking slot number
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = self._read_json(self.history_file)
            history = data.get("history", [])
            
            # Add history record
            history_entry = {
                "number_plate": number_plate,
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "fee": fee,
                "slot": slot
            }
            
            history.append(history_entry)
            data["history"] = history
            self._write_json(self.history_file, data)
            
            logger.info(f"Added history record: {number_plate}, Fee: ${fee:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding history record: {e}")
            return False
    
    def get_all_active_vehicles(self) -> List[Dict]:
        """
        Get all active vehicle entries
        
        Returns:
            list: List of active vehicle records
        """
        try:
            data = self._read_json(self.vehicles_file)
            vehicles = data.get("vehicles", [])
            
            # Convert ISO format strings back to datetime
            result = []
            for vehicle in vehicles:
                vehicle_copy = vehicle.copy()
                entry_time_str = vehicle.get("entry_time")
                vehicle_copy["entry_time"] = datetime.fromisoformat(entry_time_str)
                result.append(vehicle_copy)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting active vehicles: {e}")
            return []
    
    def get_parking_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get parking history records
        
        Args:
            limit: Maximum number of records to return (None for all)
        
        Returns:
            list: List of history records
        """
        try:
            data = self._read_json(self.history_file)
            history = data.get("history", [])
            
            # Convert ISO format strings back to datetime
            result = []
            for record in history:
                record_copy = record.copy()
                record_copy["entry_time"] = datetime.fromisoformat(record.get("entry_time"))
                record_copy["exit_time"] = datetime.fromisoformat(record.get("exit_time"))
                result.append(record_copy)
            
            # Return most recent first
            result.reverse()
            
            if limit is not None:
                result = result[:limit]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting parking history: {e}")
            return []
    
    def get_available_slots(self, total_slots: int = 1) -> List[int]:
        """
        Get list of available parking slots
        
        Args:
            total_slots: Total number of parking slots (default: 1)
        
        Returns:
            list: List of available slot numbers (1-indexed)
        """
        try:
            data = self._read_json(self.vehicles_file)
            vehicles = data.get("vehicles", [])
            
            # Get occupied slots
            occupied_slots = {v.get("slot") for v in vehicles if v.get("slot") is not None}
            
            # Find available slots
            available = [i for i in range(1, total_slots + 1) if i not in occupied_slots]
            
            return available
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return list(range(1, total_slots + 1))
    
    def is_parking_full(self, total_slots: int = 1) -> bool:
        """
        Check if parking is full
        
        Args:
            total_slots: Total number of parking slots (default: 1)
        
        Returns:
            bool: True if parking is full, False otherwise
        """
        available_slots = self.get_available_slots(total_slots)
        return len(available_slots) == 0


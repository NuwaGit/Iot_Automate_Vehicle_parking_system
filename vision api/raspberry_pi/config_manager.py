"""
Configuration Manager Module
Handles loading and saving zone configurations
"""

import json
import os
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages parking system configuration"""
    
    DEFAULT_CONFIG = {
        "entry_zone": {
            "x1": 0,
            "y1": 0,
            "x2": 640,
            "y2": 480
        },
        "exit_zone": {
            "x1": 640,
            "y1": 0,
            "x2": 1280,
            "y2": 480
        },
        "entry_virtual_line_position": 0.5,
        "exit_virtual_line_position": 0.5,
        "frame_width": 1280,
        "frame_height": 720,
        "motion_threshold": 500
    }
    
    def __init__(self, config_file="config.json"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file (relative to script directory)
        """
        # Get directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(script_dir, config_file)
        self.config = None
    
    def load_config(self) -> Dict:
        """
        Load configuration from file
        
        Returns:
            dict: Configuration dictionary
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
                return self.config
            else:
                logger.warning(f"Configuration file not found: {self.config_file}. Using defaults.")
                self.config = self.DEFAULT_CONFIG.copy()
                return self.config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}. Using defaults.")
            self.config = self.DEFAULT_CONFIG.copy()
            return self.config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}. Using defaults.")
            self.config = self.DEFAULT_CONFIG.copy()
            return self.config
    
    def save_config(self, config: Dict) -> bool:
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate configuration structure
            if not self._validate_config(config):
                logger.error("Invalid configuration structure")
                return False
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.config = config
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def _validate_config(self, config: Dict) -> bool:
        """
        Validate configuration structure
        
        Args:
            config: Configuration dictionary
        
        Returns:
            bool: True if valid, False otherwise
        """
        required_keys = ["entry_zone", "exit_zone", "entry_virtual_line_position", "exit_virtual_line_position"]
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required key: {key}")
                return False
        
        # Validate zones
        for zone_name in ["entry_zone", "exit_zone"]:
            zone = config[zone_name]
            required_zone_keys = ["x1", "y1", "x2", "y2"]
            for key in required_zone_keys:
                if key not in zone:
                    logger.error(f"Missing key in {zone_name}: {key}")
                    return False
                if not isinstance(zone[key], int):
                    logger.error(f"Invalid type for {zone_name}.{key}: must be int")
                    return False
        
        # Validate virtual line positions
        for line_name in ["entry_virtual_line_position", "exit_virtual_line_position"]:
            if not isinstance(config[line_name], (int, float)):
                logger.error(f"{line_name} must be a number")
                return False
            
            if not (0.0 <= config[line_name] <= 1.0):
                logger.error(f"{line_name} must be between 0.0 and 1.0")
                return False
        
        return True
    
    def get_entry_zone(self) -> Tuple[int, int, int, int]:
        """
        Get entry zone coordinates
        
        Returns:
            tuple: (x1, y1, x2, y2) coordinates
        """
        if self.config is None:
            self.load_config()
        
        zone = self.config["entry_zone"]
        return (zone["x1"], zone["y1"], zone["x2"], zone["y2"])
    
    def get_exit_zone(self) -> Tuple[int, int, int, int]:
        """
        Get exit zone coordinates
        
        Returns:
            tuple: (x1, y1, x2, y2) coordinates
        """
        if self.config is None:
            self.load_config()
        
        zone = self.config["exit_zone"]
        return (zone["x1"], zone["y1"], zone["x2"], zone["y2"])
    
    def get_entry_virtual_line_position(self) -> float:
        """
        Get entry virtual line position
        
        Returns:
            float: Entry virtual line position (0.0-1.0)
        """
        if self.config is None:
            self.load_config()
        
        return self.config.get("entry_virtual_line_position", 0.5)
    
    def get_exit_virtual_line_position(self) -> float:
        """
        Get exit virtual line position
        
        Returns:
            float: Exit virtual line position (0.0-1.0)
        """
        if self.config is None:
            self.load_config()
        
        return self.config.get("exit_virtual_line_position", 0.5)
    
    def get_virtual_line_position(self) -> float:
        """
        Get virtual line position (deprecated, use get_entry_virtual_line_position)
        Kept for backward compatibility
        
        Returns:
            float: Entry virtual line position (0.0-1.0)
        """
        return self.get_entry_virtual_line_position()
    
    def get_motion_threshold(self) -> int:
        """
        Get motion detection threshold
        
        Returns:
            int: Motion threshold value
        """
        if self.config is None:
            self.load_config()
        
        return self.config.get("motion_threshold", 500)
    
    def get_frame_dimensions(self) -> Tuple[int, int]:
        """
        Get frame dimensions
        
        Returns:
            tuple: (width, height)
        """
        if self.config is None:
            self.load_config()
        
        return (
            self.config.get("frame_width", 1280),
            self.config.get("frame_height", 720)
        )


"""
Serial Communication Module for Raspberry Pi
Handles UART communication with ESP32
"""

import serial
import serial.tools.list_ports
import time
import logging

logger = logging.getLogger(__name__)


class SerialCommunicator:
    """Handles serial communication with ESP32"""
    
    def __init__(self, port=None, baud_rate=115200, timeout=1):
        """
        Initialize serial communication
        
        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0' or '/dev/ttyACM0')
                  If None, will attempt to auto-detect ESP32
            baud_rate: Baud rate for communication (default: 115200)
            timeout: Read timeout in seconds (default: 1)
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_connection = None
        self.is_connected = False
        
    def connect(self):
        """Establish serial connection with ESP32"""
        try:
            # Auto-detect port if not specified
            if self.port is None:
                self.port = self._auto_detect_port()
                if self.port is None:
                    raise Exception("Could not auto-detect ESP32 serial port")
            
            # Open serial connection
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for connection to stabilize
            time.sleep(2)
            
            # Clear any existing data in buffer
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            self.is_connected = True
            logger.info(f"Serial connection established on {self.port} at {self.baud_rate} baud")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.is_connected = False
            logger.info("Serial connection closed")
    
    def _auto_detect_port(self):
        """
        Auto-detect ESP32 serial port
        Looks for common ESP32 identifiers in port descriptions
        """
        ports = serial.tools.list_ports.comports()
        
        # Common ESP32 identifiers
        esp32_identifiers = ['ESP32', 'CH340', 'CP210', 'FTDI', 'USB Serial']
        
        for port in ports:
            port_description = port.description.upper()
            for identifier in esp32_identifiers:
                if identifier.upper() in port_description:
                    logger.info(f"Auto-detected ESP32 on port: {port.device}")
                    return port.device
        
        # If no match found, try common port names
        common_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyUSB1', '/dev/ttyACM1']
        for port_name in common_ports:
            try:
                test_serial = serial.Serial(port_name, self.baud_rate, timeout=0.5)
                test_serial.close()
                logger.info(f"Found available port: {port_name}")
                return port_name
            except (serial.SerialException, OSError):
                continue
        
        return None
    
    def send_command(self, command):
        """
        Send command to ESP32
        
        Args:
            command: Command string to send (e.g., 'OPEN_ENTRY_GATE')
        
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.is_connected or not self.serial_connection.is_open:
            logger.warning("Serial connection not established. Attempting to reconnect...")
            if not self.connect():
                return False
        
        try:
            command_with_newline = command + '\n'
            self.serial_connection.write(command_with_newline.encode('utf-8'))
            self.serial_connection.flush()
            logger.debug(f"Sent command: {command}")
            return True
        except serial.SerialTimeoutException:
            logger.error("Serial write timeout")
            return False
        except serial.SerialException as e:
            logger.error(f"Serial write error: {e}")
            self.is_connected = False
            return False
    
    def read_message(self):
        """
        Read message from ESP32
        
        Returns:
            str: Message received from ESP32, or None if no message available
        """
        if not self.is_connected or not self.serial_connection.is_open:
            return None
        
        try:
            if self.serial_connection.in_waiting > 0:
                message = self.serial_connection.readline().decode('utf-8').strip()
                if message:
                    logger.debug(f"Received message: {message}")
                    return message
        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            self.is_connected = False
        except UnicodeDecodeError:
            logger.warning("Failed to decode serial message")
        
        return None
    
    def read_all_messages(self):
        """
        Read all available messages from ESP32
        
        Returns:
            list: List of messages received
        """
        messages = []
        while True:
            message = self.read_message()
            if message is None:
                break
            messages.append(message)
        return messages
    
    def is_available(self):
        """Check if serial connection is available"""
        return self.is_connected and self.serial_connection is not None and self.serial_connection.is_open
    
    def reconnect(self):
        """Attempt to reconnect to ESP32"""
        logger.info("Attempting to reconnect...")
        self.disconnect()
        time.sleep(1)
        return self.connect()


# Convenience functions for common commands
def open_entry_gate(comm: SerialCommunicator):
    """Open entry gate"""
    return comm.send_command("OPEN_ENTRY_GATE")


def close_entry_gate(comm: SerialCommunicator):
    """Close entry gate"""
    return comm.send_command("CLOSE_ENTRY_GATE")


def open_exit_gate(comm: SerialCommunicator):
    """Open exit gate"""
    return comm.send_command("OPEN_EXIT_GATE")


def close_exit_gate(comm: SerialCommunicator):
    """Close exit gate"""
    return comm.send_command("CLOSE_EXIT_GATE")


def buzzer_on(comm: SerialCommunicator):
    """Turn buzzer on"""
    return comm.send_command("BUZZER_ON")


def buzzer_off(comm: SerialCommunicator):
    """Turn buzzer off"""
    return comm.send_command("BUZZER_OFF")


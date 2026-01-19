"""
Fee Calculator Module
Calculates parking fees based on entry and exit times
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FeeCalculator:
    """Calculates parking fees"""
    
    def __init__(self, hourly_rate=10.0):
        """
        Initialize fee calculator
        
        Args:
            hourly_rate: Parking fee per hour in dollars (default: $10.00)
        """
        self.hourly_rate = hourly_rate
    
    def calculate_fee(self, entry_time: datetime, exit_time: datetime) -> float:
        """
        Calculate parking fee based on entry and exit times
        
        Args:
            entry_time: Vehicle entry timestamp
            exit_time: Vehicle exit timestamp
        
        Returns:
            float: Calculated parking fee in dollars
        """
        if entry_time is None or exit_time is None:
            logger.error("Invalid entry or exit time")
            return 0.0
        
        if exit_time < entry_time:
            logger.error("Exit time is before entry time")
            return 0.0
        
        # Calculate parking duration
        duration = exit_time - entry_time
        
        # Convert duration to hours (including fractional hours)
        hours = duration.total_seconds() / 3600.0
        
        # Calculate fee (round up to nearest hour)
        hours_rounded = self._round_up_hours(hours)
        fee = hours_rounded * self.hourly_rate
        
        logger.info(f"Parking duration: {duration}, Hours: {hours:.2f}, Fee: ${fee:.2f}")
        
        return fee
    
    def _round_up_hours(self, hours: float) -> float:
        """
        Round up hours to nearest hour
        
        Args:
            hours: Hours as float
        
        Returns:
            float: Rounded up hours
        """
        import math
        return math.ceil(hours)
    
    def format_fee(self, fee: float) -> str:
        """
        Format fee as currency string
        
        Args:
            fee: Fee amount in dollars
        
        Returns:
            str: Formatted fee string (e.g., "$10.00")
        """
        return f"${fee:.2f}"
    
    def calculate_duration_string(self, entry_time: datetime, exit_time: datetime) -> str:
        """
        Calculate and format parking duration as string
        
        Args:
            entry_time: Vehicle entry timestamp
            exit_time: Vehicle exit timestamp
        
        Returns:
            str: Formatted duration string (e.g., "2 hours 30 minutes")
        """
        if entry_time is None or exit_time is None:
            return "Invalid duration"
        
        if exit_time < entry_time:
            return "Invalid duration"
        
        duration = exit_time - entry_time
        total_seconds = int(duration.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            if minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''}"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return f"{seconds} second{'s' if seconds != 1 else ''}"


def calculate_parking_fee(entry_time: datetime, exit_time: datetime, hourly_rate=10.0) -> float:
    """
    Convenience function to calculate parking fee
    
    Args:
        entry_time: Vehicle entry timestamp
        exit_time: Vehicle exit timestamp
        hourly_rate: Parking fee per hour (default: $10.00)
    
    Returns:
        float: Calculated parking fee
    """
    calculator = FeeCalculator(hourly_rate)
    return calculator.calculate_fee(entry_time, exit_time)


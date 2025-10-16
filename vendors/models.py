from django.db import models
from django.utils import timezone
from datetime import datetime
from users.models import User

# Create your models here.

class Vendor(models.Model):
    TYPE_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('store', 'Store'),
        ('cafe', 'Cafe'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_vendors')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='vendor_logos/', null=True, blank=True)
    rating = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class Branch(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone = models.CharField(max_length=20)
    opening_hours = models.JSONField(default=dict)  # {"monday": "09:00-22:00", ...}
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor.name} - {self.name}"
    
    def get_today_hours(self):
        """Get opening hours for today"""
        from zoneinfo import ZoneInfo
        
        if not self.opening_hours:
            return None
            
        # Get current day name in local timezone (Asia/Tashkent)
        now_utc = timezone.now()
        now_local = now_utc.astimezone(ZoneInfo('Asia/Tashkent'))
        today = now_local.strftime('%A').lower()
        
        # Map English day names to possible keys
        day_mapping = {
            'monday': ['monday', 'понедельник', 'пн'],
            'tuesday': ['tuesday', 'вторник', 'вт'],
            'wednesday': ['wednesday', 'среда', 'ср'],
            'thursday': ['thursday', 'четверг', 'чт'],
            'friday': ['friday', 'пятница', 'пт'],
            'saturday': ['saturday', 'суббота', 'сб'],
            'sunday': ['sunday', 'воскресенье', 'вс']
        }
        
        # Try to find today's hours
        for key in day_mapping.get(today, [today]):
            if key in self.opening_hours:
                return self.opening_hours[key]
        
        return None
    
    def get_closing_time(self):
        """Get closing time for today"""
        today_hours = self.get_today_hours()
        if not today_hours:
            return "Не указано"
            
        # Handle different formats
        if isinstance(today_hours, str):
            # Format: "09:00-22:00", "09:00 - 22:00" or "closed"
            if today_hours.lower() in ['closed', 'закрыто']:
                return "Закрыто"
            
            # Handle both "09:00-18:00" and "09:00 - 18:00" formats
            if '-' in today_hours:
                try:
                    # Split by '-' and clean up spaces
                    parts = today_hours.split('-')
                    if len(parts) == 2:
                        close_time = parts[1].strip()
                        return close_time
                    return today_hours
                except ValueError:
                    return today_hours
            
            return today_hours
        
        elif isinstance(today_hours, dict):
            # Format: {"open": "09:00", "close": "22:00"}
            return today_hours.get('close', 'Не указано')
        
        return "Не указано"
    
    def is_open_now(self):
        """Check if branch is currently open"""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        today_hours = self.get_today_hours()
        if not today_hours:
            return False
            
        if isinstance(today_hours, str):
            if today_hours.lower() in ['closed', 'закрыто']:
                return False
                
            if '-' in today_hours:
                try:
                    # Handle both "09:00-18:00" and "09:00 - 18:00" formats
                    parts = today_hours.split('-')
                    if len(parts) == 2:
                        open_time_str = parts[0].strip()
                        close_time_str = parts[1].strip()
                        
                        # Get current time in local timezone (Asia/Tashkent)
                        now_utc = timezone.now()
                        now_local = now_utc.astimezone(ZoneInfo('Asia/Tashkent'))
                        current_time = now_local.time()
                        
                        # Parse opening and closing times
                        open_time = datetime.strptime(open_time_str, '%H:%M').time()
                        close_time = datetime.strptime(close_time_str, '%H:%M').time()
                        
                        # Check if we're within opening hours
                        if open_time <= close_time:
                            # Normal case: 09:00 - 18:00
                            return open_time <= current_time <= close_time
                        else:
                            # Overnight case: 20:00 - 02:00
                            return current_time >= open_time or current_time <= close_time
                    return False
                except (ValueError, AttributeError):
                    return False
        
        elif isinstance(today_hours, dict):
            open_time_str = today_hours.get('open')
            close_time_str = today_hours.get('close')
            if open_time_str and close_time_str:
                try:
                    # Get current time in local timezone (Asia/Tashkent)
                    now_utc = timezone.now()
                    now_local = now_utc.astimezone(ZoneInfo('Asia/Tashkent'))
                    current_time = now_local.time()
                    
                    # Parse opening and closing times
                    open_time = datetime.strptime(open_time_str, '%H:%M').time()
                    close_time = datetime.strptime(close_time_str, '%H:%M').time()
                    
                    # Check if we're within opening hours
                    if open_time <= close_time:
                        # Normal case: 09:00 - 18:00
                        return open_time <= current_time <= close_time
                    else:
                        # Overnight case: 20:00 - 02:00
                        return current_time >= open_time or current_time <= close_time
                except (ValueError, AttributeError):
                    return False
        
        return False
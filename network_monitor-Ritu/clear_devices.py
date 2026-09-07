# clear_devices.py - Delete ALL devices from database
from app import app, db
from models import Device, Log, Alert, DeviceAlertCycle

def clear_all_devices():
    with app.app_context():
        # Delete dependent tables first
        Log.query.delete()
        Alert.query.delete()
        DeviceAlertCycle.query.delete()
        device_count = Device.query.count()
        if device_count > 0:
            Device.query.delete()
            db.session.commit()
            print(f"🗑️  Cleared {device_count} devices and associated logs from database")
        else:
            print("ℹ️  No devices to clear")

if __name__ == "__main__":
    clear_all_devices()
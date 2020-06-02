"""
sableye.py - control this from mawile.
modified : 5/30/2020
     ) 0 o .
"""
import re
try:
    from .devices.i2c_adc import ADS1115, find_i2c_devices
    from .devices.cv2_camera import CV2_Camera, find_cv2_cameras
except:
    from devices.i2c_adc import ADS1115, find_i2c_devices
    from devices.cv2_camera import CV2_Camera, find_cv2_cameras


## globals.
_AVAILABLE_I2C_ADDRESSES = []
_AVAILABLE_USB_ADDRESSES = []
_AVAILABLE_CV2_ADDRESSES = []


## helpers.
# temp.
def find_usb_sensors():
    usb_devices = []
    return usb_devices

def printf(blurb, flag='status'):
    preamble = str(flag).upper() + ' : '
    blurb = preamable + blurb
    print(blurb)

##finders.
def find_sensors():
    # Find available eyes/ears/tongues/etc.
    sensors = []
    sensors += find_i2c_devices()
    sensors += find_usb_sensors()
    sensors += find_cv2_cameras()
    return sensors

# Find available heads.
def find_controllers():
    pass

# Find available limbs.
def find_mech():
    pass


def find_devices():
    sensors = find_sensors()
    controllers = find_controllers()
    mech = find_mech()
    return sensors, controllers, mech

## actions.
def connect(devices):
    for device in devices:
        try:
            device.connect()
        except:
            printf('Cannot connect to device, '+str(device), 'warning')

def disconnect(devices):
    for device in devices:
        try:
            device.disconnect()
        except:
            printf('Cannot disconnect from device, '+str(device), 'warning')

def start_recording(devices, duration=0.0):
    for device in devices:
        try:
            device.start_recording(duration=duration)
        except:
            printf('Cannot start recording with device, '+str(device), 'warning')

def stop_recording(devices):
    for device in devices:
        try:
            device.stop_recording(duration=duration)
        except:
            printf('ERROR! Cannot stop recording with device, '+str(device), 'warning')

def turn_on(devices):
    for device in devices:
        try:
            device.turn_on(duration=duration)
        except:
            printf('ERROR! Cannot turn on device, '+str(device), 'warning')

def turn_off(devices):
    for device in devices:
        try:
            device.turn_off(duration=duration)
        except:
            printf('ERROR! Cannot turn off device, '+str(device), 'warning')


# tests.
def sableye():
    sensors = find_sensors()
    controllers = find_controllers()
    mech = find_mech()

if __name__ == '__main__':
    sableye()

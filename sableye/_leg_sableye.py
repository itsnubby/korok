"""
sableye_data_collect.py - Collect data from sableye's sensors.
Public:
    * detect()
    * set_up_([Device])
    * record_from_([Device])
    * sableye__record(Device, [options])
    * sableye__stream(Device, [options])
    * sableye__pause(Device, [options])
    * sableye__close(Device, [options])
modified: 5/1/2020
  ) 0 o .
"""
# NOTE: Move this file into a new module that runs on Pis.
import os, sys, datetime, copy, json, copy
# Maintain Python2 compatibility...FOOLISHLY.
try:
    from .devices.usb_camera import USB_Camera, find_usb_cameras
    from .devices.adc import ADS1115
    from .alakazam import sort
    from .squawk import ask, say
except:
    from devices.usb_camera import USB_Camera, find_usb_cameras
    from devices.adc import ADS1115
    from alakazam import sort
    from squawk import ask, say
#finally:
#    print('Error! File \'squawk\' not found! Aborting...')
#    sys.exit(1)


## Global variables of intrigue.
_SUPPORTED = {
        'device': {
            'sensor': [
                'usb_camera'
                ]
            }
        }
## Local functions.
def _get_time_now(time_format='utc'):
    """
    Thanks Jon.  (;
    :in: time_format (str) ['utc','epoch']
    :out: timestamp (str)
    """
    if time_format == 'utc' or time_format == 'label':
        return datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    elif time_format == 'epoch' or time_format == 'timestamp':
        td = datetime.datetime.utcnow() - _EPOCH
        return str(td.total_seconds())
    else:
        # NOTE: Failure to specify an appropriate time_format will cost
        #         you one layer of recursion! YOU HAVE BEEN WARNED.  ) 0 o .
        return _get_time_now(time_format='epoch')

def _save_file(contents, save_path, option='+'):
    """
    Try to save a file.
    :in: contents (str)
    :in: save_path (str)
    :in: option (str) - {+ [append], ? [query_to_overwrite], ! [overwrite]}
    """
    action = 'w'
    if os.path.isfile(save_path):
        if option == '?':
            if option == '+' or not ask('File '+save_path+' exists. Replace?', answer_type=bool):
                action += '+'
    with open(save_path, action) as fp_save:
        fp_save.write(contents)

def _check_supported(label, support_dict):
    """
    See if we can handle it.
    """
    if label in support_dict:
        return True
    else:
        return False


## Helpers.
class DailyEvent:
    def __init__(self, minute_time):
        """
        :in: minute_time (int) minutes into day of event.
        """
        self.time = minute_time
        self.event = None

        # Aliased methods.
        self.key = self.time

    def __str__(self):
        return str(self.time)

class Redwood:
    """
    Kinda binary tree here.
    """
    def __init__(self):
        self.root = None

    def build(self, value_list):
        """
        Grow from seed.
        """


## Module definitions.
def detect(options=[]):
    """
    Identify connected sableye-enabled devices.
    Reads from a separate configuration file:
        + indexed by name, provides communications
    """
    global _SUPPORTED
#    connected_ = {'sensor': {}}
#    connected_devices['sensor']['usb_camera'] = find_usb_cameras()
    connected_devices = find_usb_cameras()
    return connected_devices

def set_up_(devices):
    """
    Calling set-up functions on a weird data device.
    :in: devices [Device]
    """
    for device in devices:
        device.set_up()
#    for device_class in connected_devices.keys():
#        for device_type in connected_devices[device_class]:
#            say(' '.join([
#                'Setting up',
#                device_type,
#                device_class,
#                'devices']), 'status')
#            for device in connected_devices[device_class][device_type]:
#                device.set_up()
    say('SABLEYE : Ready for data collection', 'success')

def record_from_(devices, duration=0.0):
    for device in devices:
        try:
            device.start_recording(duration=duration)
            say('SABLEYE : Recording from '+str(device), 'status')
        except:
            pass

def take_picture_from_(devices):
    for device in devices:
        try:
            device.take_picture()
            say('SABLEYE : Taking picture from '+str(device), 'status')
        except:
            pass

def clean_up_(devices):
    for device in devices:
        device.clean_up()
    say('SABLEYE : All clean and sparkly. (;', 'success')

def _start_data_collection(connected_devices, mode='continuous'):
    """
    Stream data from applicable devices stored in a dictionary of oddity.
    :in: connected_devices {odd}
    """
    global _SUPPORTED
    for device_type in connected_devices['sensor']:
        if _check_supported(device_type, _SUPPORTED['device']['sensor']):
            for device in connected_devices['sensor'][device_type]:
                device.start_recording(mode=mode)
    say('SABLEYE : Data collection running', 'status')

def _end_data_collection(connected_devices):
    """
    Cut the stream off.
    :in: connected_devices {obscure}
    """
    for device_type in connected_devices['sensor']:
        for device in connected_devices['sensor'][device_type]:
            device.stop_recording()
    say('SABLEYE : Data collection complete', 'success')

def _clean_up(connected_devices):
    """
    Shut down shop.
    :in: connected_devices {wow}
    """
    for device_class in connected_devices.keys():
        for device_type in connected_devices[device_class]:
            say(' '.join([
                'Cleaning up',
                device_type,
                device_class,
                'devices']), 'status')
            for device in connected_devices[device_class][device_type]:
                device.set_up()
    say('SABLEYE : git lit', 'success')

def _check_wrist(form='utc'):
    """
    :out: minutes_now (int)
    """
    current_time = datetime.datetime.utcnow()
    minutes_now = current_time.hour()*60 + current_time.minute()
    return minutes_now

def _convert_to_minutes(time_in):
    """
    :in: time_in (str) HH:MM format; UTC
    :out: _minutes_out (int) minutes from midnight that day (00:00)
    """
    hours_str, minutes_str = time_in.split(':')
    hours, minutes = int(hours_str), int(minutes_str)
    return hours*60 + minutes

def _sort_integers(_to_sort):
    """
    """

    return sorted_ints

def _reorganize_sample_times(sample_times):
    """
    We ain't optimizing here exactly, but these are cool methods so let's do 'em anyway.
    Build a binary tree of sample times as minutes.
    """
    time_tree = Tree()
    for sample_time in sample_times:
        sample_minutes.append(_convert_to_utc_minutes(sample_times))
    time_tree = _build_tree(sample_minutes)
    current_time = _check_wrist('utc')
    #TODO: put in type checking.
    reformatted_times = _sort_times(sample_times, current_time).remove(current_time)

# Module definitions.
def run_timelapse(
        connected_devices,
        duration_per=10.0, sample_times=[]):
    """
    Start data collection as a timelapse on devs.
    :in: connected_devices {dem devs}
    :in: duration_per (float)
    :in: sample_times [(int, int)] HH,MM times to sample
    """
    sample_times = _reorganize_sample_times(sample_times)
    while 1<2:
        for sample_time in sample_times:
            print('hi nub.')
        sample_time = _get_time_now('utc')
        for sensor in connected_devices['sensor']:
            sensor.start_recording(duration=duration_per)


def _test_sableye(connected_devices):
    global _SUPPORTED
    set_up_(connected_devices)
    run_timelapse(connected_devices)
    _start_data_collection(connected_devices)
    time.sleep(1)
    _end_data_collection(connected_devices)
    _clean_up(connected_devices)
    say('Test complete', 'success')

if __name__ == '__main__':
    connected_devices = detect()
    _test_sableye(connected_devices)
    

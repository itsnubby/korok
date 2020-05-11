"""
Collarct sarme Dardar.
     ) 0 o .
"""
import sys, os, time, datetime
import subprocess as sp
#try:
#import cv2
import Adafruit_ADS1x15
#except ImportError:
#    print('Use Python3 nub; exiting')
#    sys.exit(1)

## global n useful.
_ADC_ADDRESS = 0x49
_ADC_BUS = 0
_ADC_GAIN = 1

# data paths.
_BASE_DATA_PATH = ''
_ADC_DATA_PATH = ''
_CV2_DATA_PATH = ''

# image options
_IMAGE_RESOLUTION = {
        'width': '1280',
        'height': '720'
        }


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
def _get_cv2_indices():
    cv2_indices = []
    for cv2_index in range(0,9,1):
        channel = cv2.VideoCapture(cv2_index)
        if not channel is None and channel.isOpened():
            cv2_indices.append(cv2_index)
        channel.release()
        cv2.destroyAllWindows()
    return cv2_indices

def _get_cv2_channels():
    cv2_channels = []
    cv2_indices = _get_cv2_indices()
    for cv2_index in cv2_indices:
        cv2_channels.append(cv2.VideoCapture(cv2_index))
    return cv2_channels

def _set_base_data_path(base_data_path):
    global _BASE_DATA_PATH
    if not os.path.isdir(base_data_path):
        os.mkdir(base_data_path)
    _BASE_DATA_PATH = base_data_path

def _set_adc_data_path():
    global _ADC_DATA_PATH
    timestamp = _get_time_now('label')
    _ADC_DATA_PATH = '_'.join([
        _BASE_DATA_PATH+timestamp,
        'adc.csv'])
    
def _set_cv2_picture_path():
    global _CV2_DATA_PATH
    timestamp = _get_time_now('label')
    _CV2_DATA_PATH = '_'.join([
        _BASE_DATA_PATH+timestamp,
        'cv2.jpg'])

def take_pic(cv2_channel):
    ret, frame = cv2_channel.read()
    assert ret
    cv2.imwrite(_CV2_DATA_PATH)

def write_adc_data(adc_channel):
    values = [0]*4
    for sub_channel in range(4):
        values[sub_channel] = adc_channel.read_adc(sub_channel, gain=_ADC_GAIN)
    _csv_out = ', '.join([
        '{0:>6}',
        '{1:>6}',
        '{2:>6}',
        '{3:>6}']).format(*values)
    with open(_ADC_DATA_PATH, 'a+') as adcp:
        adcp.write(_csv_out)

def _get_fs_camera_addresses():
    return ['/dev/video0']

def _get_fs_picture_path(camera_address):
    timestamp = _get_time_now('label')
    return ('_'.join([
        _BASE_DATA_PATH+timestamp,
        camera_address.split('/')[-1]+'.jpg']))
    
def take_fs_pic(camera_address):
    _picture_path = _get_fs_picture_path(camera_address)
    _fs_args = [
            'fswebcam',
            '-d',
            camera_address,
            '-r',
            'x'.join([_IMAGE_RESOLUTION['width'],_IMAGE_RESOLUTION['height']]),
            _picture_path
            ]
    _fs_cmd = ' '.join(_fs_args)
    print(str(_fs_cmd))
    sp.check_output(_fs_args)


def collect_data():
    #cv2_channels = _get_cv2_channels()
    #cv2_channel = cv2_channels[0]
    usb_camera_addresses = _get_fs_camera_addresses()
    adc_channel = Adafruit_ADS1x15.ADS1115(_ADC_ADDRESS)
    #adc_channel = ADS1115(_ADC_ADDRESS)
    _set_base_data_path('./test_data/')
    _set_adc_data_path()
    while 1<2:
        for camera_address in usb_camera_addresses:
            take_fs_pic(camera_address)
        write_adc_data(adc_channel)
        time.sleep(600)     # every 10mins.


if __name__ == "__main__":
    collect_data()

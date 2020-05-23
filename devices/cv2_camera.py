"""
cv2_camera.py - Python API for USB cameras.
sableye - sensor interface
Public:
    * USB_Camera(Sensor)
    * find_cv2_cameras()
modified : 5/22/2020
  ) 0 o .
"""
import cv2, glob, time, os, datetime
try:
    from .device import Device, _MIN_PRIORITY, _MAX_PRIORITY, _DEFAULT_PRIORITY
except:
    from device import Device, _MIN_PRIORITY, _MAX_PRIORITY, _DEFAULT_PRIORITY


## GLOBALITIES.
# time stuff.
_CONNECT_TIMEOUT = 20                # 20s to connect.
_DISCONNECT_TIMEOUT = 10                # 20s to connect.
_DEFAULT_RECORD_TIME = 10           # 10s of streaming by default.


## module definitions.
def find_cv2_cameras():
    """
    Hunt down and return any USB cameras.
    :out: cv2_cameras [USB_Camera]
    """
    # TODO
    cv2_cameras = []
    camera_addresses = []
    location = '/dev/video*'
    video_ports = glob.glob(location)
    for cv_index in range(0,8,1):
        channel = cv2.VideoCapture(cv_index)
        if not channel is None and channel.isOpened():
            camera_addresses.append(cv_index)
        channel.release()
        cv2.destroyAllWindows()

    for unique_id, address in enumerate(camera_addresses):
        say('Adding camera index '+str(address))
        cv2_cameras.append(USB_Camera(str(unique_id), address))
    return cv2_cameras


class USB_Camera(Device):
    """
    Device class for USB-/OpenCV-enabled cameras.
    """
    def __init__(self, label, address):
        try:
            super().__init__(label, address, interface)
        except:
            super(USB_Camera, self).__init__(label, address, interface)

    def __str__(self):
        try:
            return str(self.id)
        except
            return 'cv2_camera'

    # redefined, read ya mind.
    def _set_up_events(self):
        self._add_event('NO_EVENT', _MIN_PRIORITY)
        self._add_event('INIT_EVENT', _MAX_PRIORITY)
        self._add_event('EXIT_EVENT', _MIN_PRIORITY)
        self._add_event('COMPLETE_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CONNECTED_EVENT', _MAX_PRIORITY)
        self._add_event('DISCONNECTED_EVENT', _MAX_PRIORITY)
        self._add_event('CONNECT_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('DISCONNECT_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('TAKE_PICUTRE_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('START_RECORDING_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('STOP_RECORDING_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CONNECT_TIMEOUT_EVENT', _MAX_PRIORITY)
        self._add_event('DISCONNECT_TIMEOUT_EVENT', _MAX_PRIORITY)
        self._add_event('RECORDING_TIMEOUT_EVENT', _MAX_PRIORITY)
        return self.events

    def _set_up_timers(self):
        # redefine this to add/remove timeouts.
        self._add_timer('connecting', _CONNECT_TIMEOUT, 'CONNECT_TIMEOUT_EVENT')
        self._add_timer('disconnecting', _DISCONNECT_TIMEOUT, 'DISCONNECT_TIMEOUT_EVENT')
        self._add_timer('recording', _DEFAULT_RECORD_TIME, 'RECORDING_TIMEOUT_EVENT')
        return self.timers

    def _set_up_interrupts(self):
        self.interrupts = {}
        return self.interrupts

    def _set_up_requests(self):
        self._add_request('CONNECT', 'CONNECT_REQUEST_EVENT')
        self._add_request('DISCONNECT', 'DISCONNECT_REQUEST_EVENT')
        self._add_request('TAKE_PICTURE', 'TAKE_PICTURE_REQUEST_EVENT')
        self._add_request('START_RECORDING', 'START_RECORDING_REQUEST_EVENT')
        self._add_request('STOP_RECORDING', 'STOP_RECORDING_REQUEST_EVENT')
        return self.requests

    # called from __init__().
    def _get_device_id(self, label):
        """
        See that sensor.
        :in: label (int) Unique id
        :out: id (str)
        """
        # 'sensor' if not redefined.
        return '-'.join(['cv2','camera',str(label)])

    def _set_data_paths(self, timestamp_label):
        _video_extension = 'avi'        # avi, mp4
        _picture_extension = 'jpg'      # png, jpg
        self._video_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                _str(self)]), _video_extension])
        self._picture_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                _str(self)]), _picture_extension])

    def _fill_info(self):
        """
        Chat up the device to find where it lives as well
          as how to get into its front door.
        :in: old_info {dict} - any old metadata 'bout the device.
        :out: info {dict}
        """
        try:
            super()._fill_info()
        except:
            super(USB_Camera, self)._fill_info()
        self.info.update({'class': 'cv2-camera'})
        
    # more even redefinedment.
    def _link_comms(self):
        """
        thread to build a bridge  ) 0 o .with a camera.
        """
        self.channel = cv2.VideoCapture(int(self.address))
        if self.channel and self.channel.isOpened():
            self.connected.value = 1

    def _break_comms(self):
        self.channel.release()
    
    # FEATURES af.
    def _capture_pic(self):
        """
        Take a single picture.
        """
        ret, frame = self.channel.read()
        assert ret
        cv2.imwrite(self._picture_path, frame)

    def _display_preview(self):
        ret, frame = self.channel.read()
        assert ret
        cv2.imshow('-'.join([
            'preview',
            str(self)]), frame)
        time.sleep(2)       # TODO : <-- make ui.
        cv2.destroyAllWindows()
    
    # TODO : put in features yo

    def _capture_video(self, preview=False):
        """
        Capture video from camera.
        :in: preview (Bool)
        """
        _resolution = {
                '720p': {
                    'width': 1280,
                    'height': 720
                    }
                }
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        f_frames = 10.0     # <-- Change frames / s here.
        this_resolution = (
                _resolution['720p']['width'],
                _resolution['720p']['height'])  # <-- Change resolution here.
        w = self.channel.get(3)     #1280
        h = self.channel.get(4)     #720 
        # TODO: test if this can be written to after being released.
        out = cv2.VideoWriter(self._video_path, fourcc, f_frames, (int(w), int(h)))
        # Stream away.
        self.stream = True
        while self.stream:
            timestamp = self._check_wrist('timestamp')
            ret, frame = self.channel.read()
            assert ret
            if not preview:
                out.write(frame)
            else:
                cv2.imshow('-'.join([
                    'preview',
                    str(self)]), frame)
        out.release()

    # Device-level state machine.
    def _record_video(self, this_event):
        """
        Stream data from device indefinitely.
        """
        # TODO: add some checks to see if USBs can handle the load of cameras
        global _STREAM_TIMER
        # TODO: make some of these globals.
        self.set_file_paths()   # Creates unique file ids.
        if self._stream_mode == 'single':
            say(str(self)+' : trying it out nub')
            self._capture_image()
        else:
            if self._stream_mode == 'timed':      # Start timeout.
                self._set_timer(_STREAM_TIMER, self._stream_duration)
            self._capture_video()
        
        event = (0, 'stream_stopped')
        self._post_event(event)

    def _take_pic(self, this_event):
        pass

    def _stream(self, (this_priority, this_event)):
        """
        Streaming for a preset time.
        """
        global _STREAM_TIMER
        if this_event == 'init':
            say(str(self)+' : stream opening')
            self._start_thread(self._run_stream, 'streaming')
        elif this_event == 'timeout_'+str(_STREAM_TIMER) or this_event == 'stop_received':
            say(str(self)+' : closing stream')
            self.stream = False
        elif this_event == 'stream_stopped':
            say(str(self)+' : stream closed', 'success')
            self.migrate_state('standing_by')
        elif this_event == 'disconnect_received' or this_event == 'disconnected':
            say(str(self)+' : stream interrupted; attempting to disconnect', 'warning')
            self.stream = False
            self.migrate_state('disconnecting')
        else:
            time.sleep(0.1)

    def start_recording(self, duration=0.0):
        """
        Turn it on.
        :in: duration (float) streaming time [s]; duration <= 0.0 == continuous streaming!!
        """
        # TODO: Add state check.
        if duration <= 0.0:
            self._stream_mode = 'continuous'
        else:
            self._stream_mode = 'timed'
            self._stream_duration = duration

        event = (1, 'stream_received')
        self._post_event(event)

    def stop_recording(self):
        """
        Turn it off.
        """
        # TODO: Add state check.
        event = (1, 'stop_received')
        self._post_event(event)

    def take_picture(self):
        """
        Camera-specific.
        """
        # TODO: Add state check.
        say(str(self)+' : taking a pic')
        self._stream_mode = 'single'
        event = (1, 'stream_received')
        self._post_event(event)
        self.wait_for_('streaming')       # Wait for pictures to be taken.
        self.wait_for_('standing_by')

    def clean_up(self):
        """
        Close down shop.
        :out: success (Bool)
        """
        if not self.state == 'sleeping':
            say('Shutting down '+str(self))
            event = (1, 'disconnect_received')
            self._post_event(event)
        else:
            say('Already shut down', 'success')
        


def __test__cv2_camera():
    cv2_cameras = find_cv2_cameras()
    for cv2_camera in cv2_cameras:
        cv2_camera.set_up()
    for cv2_camera in cv2_cameras:
        cv2_camera.wait_for_('standing_by')
#    for cv2_camera in cv2_cameras:
#        cv2_camera.start_recording()
#    time.sleep(10)
#    for cv2_camera in cv2_cameras:
#        cv2_camera.stop_recording()
    for cv2_camera in cv2_cameras:
        cv2_camera.take_picture()
#    for thing in cv2_cameras:
#        say('Setting up')
#        thing.set_up()
#        say('Setup successful', 'success')
    for thing in cv2_cameras:
        thing.clean_up()
    say('Later nerd', 'success')

if __name__ == '__main__':
    __test__cv2_camera()

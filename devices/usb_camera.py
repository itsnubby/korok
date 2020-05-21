"""
usb_camera.py - Python API for USB cameras.
sableye - sensor interface
Public:
    * USB_Camera(Sensor)
    * find_usb_cameras()
modified : 4/20/2020
  ) 0 o .
"""
import cv2, glob, time, os, datetime
try:
    from .device import Device, say
except:
    from device import Device, say


## Global declarations or something.
_EPOCH = datetime.datetime(1970,1,1)

## Local functions
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

def find_usb_cameras():
    """
    Hunt down and return any USB cameras.
    :out: usb_cameras [USB_Camera]
    """
    # TODO
    usb_cameras = []
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
        usb_cameras.append(USB_Camera(str(unique_id), address))
    return usb_cameras

# GLOBALITIES.
_CONNECT_TIMEOUT = 20                # 20s to connect.
_DISCONNECT_TIMEOUT = 10                # 20s to connect.
_DEFAULT_RECORD_TIME = 10           # 10s of streaming by default.
# priorities.
_MIN_PRIORITY = 0
_MAX_PRIORITY = _MIN_PRIORITY + 5
_DEFAULT_PRIORITY = _MIN_PRIORITY + 1

class USB_Camera(Device):
    """
    Device class for USB-/OpenCV-enabled cameras.
    """
    def __init__(self, label, address):
        try:
            super().__init__(label, address, interface)
        except:
            super(USB_Camera, self).__init__(label, address, interface)

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
        self._add_event('OPEN_STREAM_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CLOSE_STREAM_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CONNECT_TIMEOUT_EVENT', _MAX_PRIORITY)
        self._add_event('DISCONNECT_TIMEOUT_EVENT', _MAX_PRIORITY)
        return self.events

    def _set_up_timers(self):
        # redefine this to add/remove timeouts.
        self._add_timer('connecting', _CONNECT_TIMEOUT, 'CONNECT_TIMEOUT_EVENT')
        self._add_timer('disconnecting', _DISCONNET_TIMEOUT, 'DISCONNECT_TIMEOUT_EVENT')
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

    # TODO        

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
        self.info.update({'class': 'usb-camera'})
        
    def _get_device_id(self, label):
        """
        See that sensor.
        :in: label (int) Unique id
        :out: id (str)
        """
        # 'sensor' if not redefined.
        return '-'.join(['usb','camera',str(label)])

    def set_file_paths(self, path_base='./test_data/'):
        """
        Set the base path to use to direct output data flow.
        :in: path_base (str) working directory [default './test_data/']
        :out: new_path_base (str) 
        """
        _video_extension = 'avi'        # avi, mp4
        _picture_extension = 'jpg'      # png, jpg
        # Check that base directory exists.
        if not os.path.isdir(path_base):
            say('Creating '+path_base)
            os.mkdir(path_base)
        # Generate unique id a la timestamp.
        timestamp_label = _get_time_now('label')
        new_path_base = '_'.join([
                path_base+timestamp_label,
                self.id])
        self._video_path = '.'.join([
            new_path_base,
            _video_extension])
        self._picture_path = '.'.join([
            new_path_base,
            _picture_extension])

    def _open_connection(self):
        """
        Thread to build a bridge with USB camera.
        """
        attempt = 1
        while self.state == 'connecting':
            self.channel = cv2.VideoCapture(int(self.address))
            say('Capturing from '+str(self.address))
            if self.channel and self.channel.isOpened():
                event = (0, 'connected')
                self._post_event(event)
                break
            self.channel.release()
            say(str(self)+' : connection attempt '+str(attempt)+' failure', 'warning')
            attempt += 1
    
    def _test_connection(self):
        """
        Check a port index through CV2.
        :in: port_index (int) cv2-friendly port to check
        :out: available (Bool) is device ready for communication?
        """
        try:
            if self.channel and self.channel.isOpened():
                return True
        except:
            pass
        return False

    def _capture_image(self,  preview=False):
        """
        Take a single picture.
        """
        ret, frame = self.channel.read()
        assert ret
        if not preview:
            say(str(self)+' : writing image to '+str(self._picture_path))
            cv2.imwrite(self._picture_path, frame)
        else:
            cv2.imshow('-'.join([
                'preview',
                str(self)]), frame)
            cv2.destroyAllWindows()     # TODO: <-- Make this reachable by interrupt.
    
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
            timestamp = _get_time_now('timestamp')
            ret, frame = self.channel.read()
            assert ret
            if not preview:
                out.write(frame)
            else:
                cv2.imshow('-'.join([
                    'preview',
                    str(self)]), frame)
        out.release()

    def _run_stream(self):
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


    # Device-level state machine.
    def _sleep(self, (this_priority, this_event)):
        """
        Sleepin'.
        """
        if this_event == 'connect_received':
            self.migrate_state('connecting')
        else:
            time.sleep(0.1)

    def _connect(self, (this_priority, this_event)):
        """
        Connect to a camera over OpenCV.
        * Set a timeout using self._set_timeout()!
        """
        global _CONNECTION_TIMER, _CONNECTION_TIMEOUT
        if this_event == 'init':
            say('Connecting to '+str(self))
            self._start_thread(self._open_connection, 'connecting')
            self._set_timer(_CONNECTION_TIMER, _CONNECTION_TIMEOUT)
        elif this_event == 'connected':
            say(str(self)+' : connection established', 'success')
            self.migrate_state('standing_by')
        elif this_event == 'timeout_'+str(_CONNECTION_TIMER):
            say(str(self)+' : timeout connecting to '+str(self)+'; disconnecting', 'warning')
            self.migrate_state('disconnecting')
        else:
            time.sleep(0.1)

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

    def _stand_by(self, (this_priority, this_event)):
        """
        Idling about.
        """
        if this_event == 'init':
            say(str(self)+' : standing by for input')
        elif this_event == 'stream_received':
            self.migrate_state('streaming')
        elif this_event == 'disconnect_received':
            self.migrate_state('disconnecting')
        else:
            time.sleep(0.1)

    def _disconnect(self, (this_priority, this_event)):
        """
        Disconnecting.
        """
        if this_event == 'init' or this_event == 'timeout_1':
            say(str(self)+' disconnecting')
            self.channel.release()
            cv2.destroyAllWindows() # <-- make sure that you can get rid of this.
            if not self.channel.isOpened():
                self.migrate_state('sleeping')
        else:
            time.sleep(0.1)

    def _run(self):
        """
        Check for events, update state broh.
        """
        while True:
            this_event = self._get_event()
            if self.state == 'sleeping':
                self._sleep(this_event)
            elif self.state == 'connecting':
                self._connect(this_event)
            elif self.state == 'standing_by':
                self._stand_by(this_event)
            elif self.state == 'streaming':
                self._stream(this_event)
            elif self.state == 'disconnecting':
                self._disconnect(this_event)
            else:
                say('Out of state, outta mind, and in '+str(self.state), 'error')
            self._update()

    def set_up(self,options={}):
        """
        Setup a USB camera.
        :out: success (Bool)
        :in: options {}
        """
        if not self.state == 'sleeping':
            say('Attempting to set up an existing device.', 'warning')
        say('Setting up')
        event = (1, 'connect_received')
        self._post_event(event)

    def wait_for_(self, state):
        """
        Wait for this to be in some state.
        :in: state (str)
        """
        while 1<2:
            if self.state == state:
                break
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
        


def __test__usb_camera():
    usb_cameras = find_usb_cameras()
    for usb_camera in usb_cameras:
        usb_camera.set_up()
    for usb_camera in usb_cameras:
        usb_camera.wait_for_('standing_by')
#    for usb_camera in usb_cameras:
#        usb_camera.start_recording()
#    time.sleep(10)
#    for usb_camera in usb_cameras:
#        usb_camera.stop_recording()
    for usb_camera in usb_cameras:
        usb_camera.take_picture()
#    for thing in usb_cameras:
#        say('Setting up')
#        thing.set_up()
#        say('Setup successful', 'success')
    for thing in usb_cameras:
        thing.clean_up()
    say('Later nerd', 'success')

if __name__ == '__main__':
    __test__usb_camera()

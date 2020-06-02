"""
i2c_adc.py - Wrap your I2C devices up nicely in Python.
Radish'n'bots, LLC
modified : 5/29/2020
     ) 0 o .
"""
import time, sys, re, multiprocessing
import subprocess as sp
try:
    from .device import Device, _MIN_PRIORITY, _MAX_PRIORITY, _DEFAULT_PRIORITY
except:
    from device import Device, _MIN_PRIORITY, _MAX_PRIORITY, _DEFAULT_PRIORITY
try:
    import Adafruit_ADS1x15
except:
    print('And lo! Download the \'Adafruit_ADS1x15\' package to use the ADS1115 ADC.')


## GLOBALISM.
# time stuff.
_CONNECT_TIMEOUT = 20               # 20s to connect.
_DISCONNECT_TIMEOUT = 10            # 10s to connect.
_STREAM_TIMEOUT = 10000             # >> a while.
_DEFAULT_RECORD_TIME = 10           # 10s default recording.
# adc stuff.
_DEFAULT_ADC_GAIN = 1
_DEFAULT_ADC_DATA_RATE = 128


## local definitions.
def find_i2c_addresses():
    """
    Hunt down and return any connected ADCs.
    """
    # get i2c addresses through a shell command.
    i2c_addresses = []
    _shelly = [
            'i2cdetect',
            '-y',
            '1'
            ]
    try:
        _i2c_list_proc = sp.Popen(_shelly, stdout=sp.PIPE)
    except:
        print('Could not communicate with shell!')
        return i2c_addresses

    # parse out i2c addresses.
    while 1<2:
        _i2c_line_str = str(_i2c_list_proc.stdout.readline().decode(encoding='UTF-8')).strip()
        # exit loop if out of lines.
        time.sleep(0.3)
        if _i2c_line_str == '':
            break
        _i2c_fields = _i2c_line_str.split(' ')
        # regex shiz.
        _regex = re.compile('[0-9]{2}')
        # skip the first line.
        if _i2c_fields[0].find(':')!=-1:
            for index in range(1,len(_i2c_fields)):
                address = _i2c_fields[index]
                if _regex.match(address):
                    address = str(address)
                    i2c_addresses.append(address)
    return i2c_addresses


## Module-definitions.
def find_i2c_devices():
    i2c_devices = []
    i2c_addresses = find_i2c_addresses()
    for index, address in enumerate(i2c_addresses):
        # TODO : make tests for each device type and a bigger interface class.
        newDevice = ADS1115(str(index), address)
        i2c_devices.append(newDevice)
    return i2c_devices

class ADS1115(Device):
    """
    Wrapper for ADS1115 ADC.
    """
    def __init__(self, label, address):
        try:
            super().__init__(label, address)
        except:
            super(ADS1115, self).__init__(label, address)
        self.streaming = multiprocessing.Value('i', 0)      # TODO : switch to flag.
        self.busnum = 1
        self.record_time = 0.0
        self.f_sample = 2.0
        self.T_sample = 1 / self.f_sample

    # redefined, read ya mind.
    def _set_up_events(self):
        self._add_event('NO_EVENT', _MIN_PRIORITY)
        self._add_event('INIT_EVENT', _MAX_PRIORITY)
        self._add_event('EXIT_EVENT', _MIN_PRIORITY)
        self._add_event('COMPLETE_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CONNECTED_EVENT', _MAX_PRIORITY)
        self._add_event('RECORDING_COMPLETE_EVENT', _MAX_PRIORITY)
        self._add_event('DISCONNECTED_EVENT', _MAX_PRIORITY)
        self._add_event('CONNECT_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('DISCONNECT_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('START_STREAMING_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('STOP_STREAMING_REQUEST_EVENT', _DEFAULT_PRIORITY)
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
        self._add_timer('streaming', _STREAM_TIMEOUT, 'STREAMING_TIMEOUT_EVENT')
        self._add_timer('recording', _DEFAULT_RECORD_TIME, 'RECORDING_TIMEOUT_EVENT')
        return self.timers

    def _set_up_interrupts(self):
        self.interrupts = {}
        return self.interrupts

    def _set_up_requests(self):
        self._add_request('CONNECT', 'CONNECT_REQUEST_EVENT')
        self._add_request('DISCONNECT', 'DISCONNECT_REQUEST_EVENT')
        self._add_request('START_STREAMING', 'START_STREAMING_REQUEST_EVENT')
        self._add_request('STOP_STREAMING', 'STOP_STREAMING_REQUEST_EVENT')
        self._add_request('START_RECORDING', 'START_RECORDING_REQUEST_EVENT')
        self._add_request('STOP_RECORDING', 'STOP_RECORDING_REQUEST_EVENT')
        return self.requests

    def _set_up_options(self):
        option_lut = {
                'record': False,
                'gain': _DEFAULT_ADC_GAIN,
                'write': True,
                'preview': False,
                'mode': 'continuous'        # << TODO : get rid o dis.
                }
        return option_lut

    # called from __init__().
    def _get_device_id(self, label):
        """
        See that sensor.
        :in: label (int) Unique id
        :out: id (str)
        """
        # 'sensor' if not redefined.
        return '-'.join(['ads1115',str(label)])

    def _get_device_address(self, address_str):
        return int(address_str, 16)

    def _set_data_paths(self, timestamp_label):
        _data_extension = 'csv'
        self._data_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                str(self)]), _data_extension])

    def _fill_info(self):
        """
        Chat up the device to find where it lives as well
          as how to get into its front door.
        :in: new_info {dict} - any old metadata 'bout the device.
        :out: info {dict}
        """
        self.info = {
                'address': str(self.address),
                'id': str(self.id),
                'options': self.option,
                'stream_duration': self.current_time - self.start_time,
                'version': 0.9
            }

    def _set_up_daemon(self):
        _initial_state = 'SLEEPING'
        state_handlers = [
                ('SLEEPING', self._sleep),
                ('CONNECTING', self._connect),
                ('STANDING_BY', self._idle),
                ('STREAMING', self._stream),        # TODO : combine streaming and recording.
                ('DISCONNECTING', self._disconnect)
                ]
        for state, handler in state_handlers:
            self.add_state(state, handler)
        self.set_up(start_state=_initial_state)
        
    # FEATURistic.
    def _set_record_time(self, duration):
        _duration = float(duration)
        self.record_time = _duration
        self.info['record_duration'] = _duration    # << TODO : make less dum.
        self._set_timer('recording', _duration)

    def _test_sub_channel(self, sub_channel):
        """
        Make sure that sub channel can be read.
        """
        # TODO: add conditionals based on DEVICE_STATE.
        _prev_value = 0
        _reps_to_fail = 30      # How many times a read value is repeated before failing.
        _reps = 0               # Gimme some more reps.
        while 1<2:
            _value = 0
            _value = self.channel.read_adc(sub_channel, gain=self.option['gain'])
            if _value == _prev_value:
                time.sleep(self.T_sample)
                _reps += 1
                continue
                if _reps >= _reps_to_fail:
                    return False
            return True

    def _find_sub_channels(self):
        # TODO: build out Channel/SubChannel ADTs.
        self._sub_channels = []             # Clear sub-channels first.
        for sub_channel in range(4):
            try:
                if self._test_sub_channel(sub_channel):
                    self._sub_channels.append(sub_channel)
            except IOError:
                self.printf('Address invalid!')
                continue
            except:
                self.printf('Unknown error')

    # state machine apendages.
    def _link_comms(self):
        """
        thread to build a bridge  ) 0 o .with a camera.
        """
        # Attempt to connect to main channel.
        self.channel = Adafruit_ADS1x15.ADS1115(address=self.address, busnum=self.busnum)
        if self.channel:
            # Find available ADC channels.
            self._find_sub_channels()
            self.printf('Connected')
            self.connected.value = 1

    def _break_comms(self):
        self.channel = None     # TODO : test if we can reconnect after this.
        if not self.channel:
            self.printf('Disconnected')
            self.connected.value = 0

    def _test_comms(self):
        # test communications with device; DAEMON.
        if self.connected.value > 0:
            if self.state == 'CONNECTING':
                self._post_event('CONNECTED_EVENT')
        elif self.connected.value == 0:
            if self.state == 'DISCONNECTING':
                self._post_event('DISCONNECTED_EVENT')

#    def _test_connection(self):
#        """
#        Check yer I2C port.
#)        :out: available (Bool) is device ready for communication?)
#        """
#        # TODO: make fully funky.
#        for sub_channel in self._sub_channels:
#            if self.channel.read_adc(sub_channel, gain=_DEFAULT_ADC_GAIN):
#                return True
#        return False
#

    def _broadcast(self, _data_str):
        if self.option['write']:
            self._write_file(self._data_path, _data_str)
        if self.option['preview']:
            pass

    def _get_data(self):
        _data_train = []
        for sub_channel in self._sub_channels:
#            try:
            _data_line = self.channel.read_adc(sub_channel, gain=self.option['gain'])
            _data_train.append(str(_data_line))
#            except:
#                pass
        return ', '.join(_data_train)+'\n'


    def _stream_data(self):
        self._set_file_paths()      # metadata, data
        self.start_time = self.current_time
        self.streaming.value = 1
        while self.streaming.value > 0:
            try:
                _data_line = self._get_data()
                self._broadcast(_data_line)
            except:
                break

    
    # ESMachine redefinements/additions.
    def _idle(self, this_event):
        if this_event == 'INIT_EVENT':
            self.printf('Standing by')
        elif this_event == 'START_STREAMING_REQUEST_EVENT':
            self._next_state = 'STREAMING'
        elif this_event == 'DISCONNECT_REQUEST_EVENT':
            self._next_state = 'DISCONNECTING'
        else:
            time.sleep(0.1)

    def _stream(self, this_event):
        """
        From device to ???.
        """
        if this_event == 'INIT_EVENT':
            self.printf('Opening stream')
            self._start_timer('streaming')
            if self.option['mode'] != 'continuous' and self.option['record']:
                self.printf('Recording : '+str(self.channel)+' for '+str(self.record_time))
                self._start_timer('recording')
            self._start_thread(self._stream_data, 'STREAMER')
        elif this_event == 'RECORDING_TIMEOUT_EVENT' or this_event == 'STOP_RECORDING_REQUEST_EVENT':

            self.generate_metadata()
            self.option['record'] = False      # TODO : verify that this changes in writer thread.
            self.printf('Streaming complete')
            self._next_state = 'STANDING_BY'
        elif this_event == 'STREAMING_TIMEOUT_EVENT' or this_event == 'STOP_STREAMING_REQUEST_EVENT':
            self.generate_metadata()
            self.streaming.value = 0
            self.printf('Streaming complete')
            self._next_state = 'STANDING_BY'
        else:
            time.sleep(0.3)

    def start_streaming(self):
        """
        Stream it.
        """
        self._incoming_requests.put((_DEFAULT_PRIORITY, 'START_STREAMING'))

    def stop_streaming(self):
        """
        Stream it.
        """
        self._incoming_requests.put((_DEFAULT_PRIORITY, 'STOP_STREAMING'))

    def start_recording(self, duration=0.0):
        """
        Turn it on.
        :in: duration (float) streaming time [s]; duration <= 0.0 == continuous streaming!!
        """
        # TODO: add state check.
        self._set_option('record', True)
        if duration > 0.0:
            self._set_option('mode', 'timed')
            self._set_record_time(duration)
        else:
            self._set_option('mode', 'continuous')
        self.start_streaming()

    # aliases.
    stop_recording = stop_streaming


def test_adc():
    """
    Ensure that all systems are a big GO.    ) 0 o .
    """
    # Edit overall test duration (s):
    test_duration = 60
    adcs = []
    try:
        # Find I2C connections.
        i2c_addresses = find_i2c_addresses()
        for index, address in enumerate(i2c_addresses):
            print(str(address))
            adcs.append(ADS1115(str(index), address))
        # Try to connect.
        for nerd in adcs:
            nerd.connect()
        # Wait for timeouts. << TODO : make more responsive.
        for nerd in adcs:
            nerd._wait_for_('STANDING_BY')
#        for nerd in adcs:
#            # Make sure that all devices are properly hooked up.
#            if not nerd.is_connected:
#                adcs.remove(nerd)
        while(1<2):
            for nerd in adcs:
                nerd.start_recording()
            time.sleep(_DEFAULT_RECORD_TIME)
            for nerd in adcs:
                nerd.stop_recording()
            for nerd in adcs:
                nerd._wait_for_('STANDING_BY')
    except KeyboardInterrupt:
        print('kraww.    ) 0 o .')
        sys.exit()


    # Sample data from I2C sensors over the desired time frame.
    #print(this_dude.channel.value, this_dude.channel.voltage)

if __name__ == '__main__':
    test_adc()

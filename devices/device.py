"""
device.py - A generic as HECK device superclass.
sableye - sensor interface
Public:
    * Device(object)
modified : 5/18/2020
  ) 0 o .
"""
import os, time, datetime, json, threading, multiprocessing, copy
import subprocess as sp
try:
    from .squawk import say
    from .control import ESMachine
    from .eventful import PriorityEvent, PriorityEventQueue
except:
    from squawk import say
    from control import ESMachine
    from eventful import PriorityEvent, PriorityEventQueue


## global declarations or something.
# time/r stuff.
_EPOCH = datetime.datetime(1970,1,1)
# priorities.
_MAX_PRIORITY = 0       #_MIN_PRIORITY + 5
_MIN_PRIORITY = _MAX_PRIORITY + 5       #0
_DEFAULT_PRIORITY = _MAX_PRIORITY + 1   #_MIN_PRIORITY + 1


## Local functions.

class Device(ESMachine):
    """
    Your one-stop-shop for device communications.
    """
    def __init__(self, label, address):
        """
        To inherit:
            * redefine _fill_info and _get_device_id appropriately.
            * call this __init__ from the child Device.
        :in: label (int) Unique ID
        :in: address
        :in: interface
        """
        # id/info stuff.
        label = str(label)
        self.id = self._get_device_id(label)
        self.address = self._get_device_address(address)
        self.info = {}      # TODO
        self.option = self._set_up_options()
        try:
            super().__init__(label)
        except:
            super(Device, self).__init__(label)
        # control flow stuff.
        self.connected = multiprocessing.Value('i',0)       # 0 == unconnected, >0 == connected
        self._set_up_daemon()
        # non-state-machine process tracking.
        self._active_threads = []
        self._active_processes = []
        self._shared_space_queue = multiprocessing.Queue()      # pass this to processes that need to make changes to shared memory space.
        # set up logging.
        self._metadata_path, self._data_path = '', ''
        self._base_path = './test_data/'
        self._set_file_paths()
        # start yer daemon up.
        self.run()

    def __str__(self):
        try:
            return str(self.id)
        except:
            return 'device'
    
    def _set_option(self, key, value):
        # set options that are output as metadata and may affect function.
        self.option[key] = value

    ## ui
    def is_connected(self):
        if self.connected.value == 0:
            return False
        return True

    # redefined as requested.
    def _set_up_events(self):
        self._add_event('NO_EVENT', _MIN_PRIORITY)
        self._add_event('INIT_EVENT', _MAX_PRIORITY)
        self._add_event('EXIT_EVENT', _MIN_PRIORITY)
        self._add_event('COMPLETE_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CONNECTED_EVENT', _MAX_PRIORITY)
        self._add_event('DISCONNECTED_EVENT', _MAX_PRIORITY)
        self._add_event('CONNECT_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('DISCONNECT_REQUEST_EVENT', _DEFAULT_PRIORITY)
        self._add_event('CONNECT_TIMEOUT_EVENT', _MAX_PRIORITY)
        self._add_event('DISCONNECT_TIMEOUT_EVENT', _MAX_PRIORITY)
        return self.events

    def _set_up_timers(self):
        # redefine this to add/remove timeouts.
        self._add_timer('connecting', 10.0, 'CONNECT_TIMEOUT_EVENT')
        self._add_timer('disconnecting', 10.0, 'DISCONNECT_TIMEOUT_EVENT')
        return self.timers

    def _set_up_interrupts(self):
        self.interrupts = {}
        return self.interrupts

    def _set_up_requests(self):
        self._add_request('CONNECT', 'CONNECT_REQUEST_EVENT')
        self._add_request('DISCONNECT', 'DISCONNECT_REQUEST_EVENT')
        return self.requests

    def _set_up_options(self):
        return {} 

    # called from __init__().
    def _get_device_id(self, label):
        """
        Hunt down the device ID.
        :in: label (int) Unique ID
        :out: id (str)
        """
        # 'device' if not redefined!
        return '-'.join(['device',label])

    def _get_device_address(self, address_str):
        # convert address string into proper format.
        return str(address_str)

    def _set_up_daemon(self):
        # NOTE : Redefine for different device types.
        _initial_state = 'SLEEPING'
        state_handlers = [
                ('SLEEPING', self._sleep),
                ('CONNECTING', self._connect),
                ('STANDING_BY', self._idle),
                ('DISCONNECTING', self._disconnect)
                ]
        for state, handler in state_handlers:
            self.add_state(state, handler)
        self.set_up(start_state=_initial_state)

    ## toolbelt.
    # file interractions.
    def _write_file(self, path, data, write_option='', overwrite=False):
        _write_options = ['w','w+','a','a+']
        _default_write_option = 'a+'
        if not write_option or write_option not in _write_options:
            write_option = _default_write_option
        if os.path.isfile(path) and write_option.find('a')==-1:
            if overwrite:
                write_option = 'w+'
            else:
                say('Could not write file '+path+' with write option '+write_option, 'warning')
                return False
        with open(path, write_option) as fp:
            fp.write(data)
        return True

    def _read_txt(path):
        with open(path, 'r+') as tfp:
            data = tfp.read()
        return data

    def _read_csv(path):
        data = []
        with open(path, 'r+') as cfp:
            for line in cfp:
                try:
                    data.append(line.split(','))
                except AttributeError:
                    pass
        return data

    def _read_json(path):
        data = {}
        with open(path, 'r+') as jfp:
            data = json.load(jfp)
        return data

    def _read_file(self, path):
        encoding = path.split('.')[-1]      # file extension.
        _encodings = ['txt','csv','json']
        _default_encoding = 'txt'
        if not encoding in _encodings:
            encoding = 'txt'
        _decoder = {
                'txt': self._read_txt(path),
                'csv': self._read_csv(path),
                'json': self._read_json(path)
                }
        return _decoder[encoding]

    def _build_base_path(self):
        _path_bits = self._base_path.split('/')
        _full_path = ''
        for _bit in _path_bits:
            _full_path += _bit + '/'
            if not os.path.isdir(_full_path) and _bit:
                try:
                    os.mkdir(_full_path)
                    self.printf('...'+_full_path)
                except:
                    self.printf('Coudn\'t mkdir '+_full_path)


    def _set_file_paths(self):
        if not os.path.isdir(self._base_path):
            print(str(self._base_path))
            self._build_base_path()
        timestamp_label = self._check_wrist('label')
        self._set_metadata_path(timestamp_label)
        self._set_data_paths(timestamp_label)

    def _set_metadata_path(self, timestamp_label):
        self._metadata_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                'metadata']), 'json'])

    def _set_data_paths(self, timestamp_label):
        # REDEFINE if more than one data file possible.
        _file_extension = 'log'
        self_data_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                str(self)]), _file_extension])

    # metadata generation.
    def _fill_info(self):
        # REDEFINE for each device.
        """
        Chat up the device to find where it lives as well
          as how to get into its front door.
        :in: new_info {dict} - any old metadata 'bout the device.
        """
        self.info = {
                'address': str(self.address),
                'id': str(self.id),
                'options': self.option
            }

    # device-specific functionalities to be redefined.
    def _link_comms(self):
        # connect to a device.
        time.sleep(4)
        time.sleep(20)
        self.connected.value += 1

    def _break_comms(self):
        # TODO : add test for disconnected. (not _test_comms)
        time.sleep(4)
        self.connected.value = 0
        time.sleep(2)

    def _test_comms(self):
        # test communications with device.
        if self.connected.value > 0:
            if self.state == 'CONNECTING':
                self._post_event('CONNECTED_EVENT')
            self.printf(str(self)+' currently connected')
        elif self.connected.value == 0:
            if self.state == 'DISCONNECTING':
                self._post_event('DISCONNECTED_EVENT')
            self.printf(str(self)+' currently disconnected')


    ## device-level state machine.
    def _wait_for_(self, state):
        # nice for debugging. (;;
        while not self.state == state:
            time.sleep(0.1)

    def _sleep(self, this_event):
        """
        Sleeping.
        """
        if this_event == 'INIT_EVENT':
            self.printf('Sleeping')
        elif this_event == 'CONNECT_REQUEST_EVENT':
            self._next_state = 'CONNECTING'
        else:
            time.sleep(0.3)
        
    def _connect(self, this_event):
        """
        Connecting.
        """
        # init : attempt to connect, start timeout.
        if this_event == 'INIT_EVENT':
            self.printf('Connecting')
            self._start_timer('connecting')     # <-- adjust this timeout for fine tuning.
            self._start_thread(self._link_comms, 'CONNECTOR')
        elif this_event == 'CONNECT_TIMEOUT_EVENT':
            print('TIME')
            self._next_state = 'SLEEPING'
        elif this_event == 'CONNECTED_EVENT':
            self._next_state = 'STANDING_BY'
        elif this_event == 'DISCONNECT_REQUEST_EVENT':
            self._next_state = 'DISCONNECTING'
        else:
            time.sleep(0.3)
            self._test_comms()
            time.sleep(0.3)

    def _disconnect(self, this_event):
        if this_event == 'INIT_EVENT':
            self.printf('Disco nnecting...')
            self._start_timer('disconnecting')
            self._start_thread(self._break_comms, 'DISCONNECTOR')
        elif this_event == 'DISCONNECTED_EVENT':
            self._next_state = 'SLEEPING'
        elif this_event == 'DISCONNECT_TIMEOUT_EVENT':
            say('Channel clogged; cannot disconnect', 'error')
            self._next_state = 'SLEEPING'
        else:
            time.sleep(0.3)
            self._test_comms()
            time.sleep(0.3)

    def _idle(self, this_event):
        """
        Standing by.
        """
        if this_event == 'INIT_EVENT':
            self.printf('Standing by')
        elif this_event == 'DISCONNECT_REQUEST_EVENT':
            self._next_state = 'DISCONNECTING'
        else:
            time.sleep(0.1)

    # user request handlers.
    def connect(self):
        """
        Setup a device.
        :in: options (dict) - Defined by specific device.
            * file_extension (str) txt [default]
        :out: success (Bool)
        """
        self._incoming_requests.put((_DEFAULT_PRIORITY, 'CONNECT'))

    def disconnect(self):
        """
        Close down shop.
        """
        self._incoming_requests.put((_DEFAULT_PRIORITY, 'DISCONNECT'))

    # datatype definitions.
    def generate_metadata(self):
        """
        Output metadata as a .json dictionary.
        """
        say('Generating metadata for '+self.id)
        self._fill_info()
        timestamp_label = self._check_wrist('label')
        metadata_path = '_'.join([
            self._base_path+timestamp_label,
            self.id+'.json'])
        metadata_str = json.dumps(
                self.info,
                sort_keys=True,
                indent=4)
        self._write_file(metadata_path, metadata_str, 'a+')


## testers.
def _test_device():
    _dummy = {
            'label': 'dummy',
            'address': '/dev/null'
            }
    ddevice = Device(_dummy['label'],_dummy['address'])
    while 1<2:
        try:
            ddevice.connect()
            ddevice._wait_for_('STANDING_BY')
            time.sleep(1)
            ddevice.disconnect()
            time.sleep(5)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    _test_device()

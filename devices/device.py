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
_MIN_PRIORITY = 0
_MAX_PRIORITY = _MIN_PRIORITY + 5
_DEFAULT_PRIORITY = _MIN_PRIORITY + 1


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
        self.info = {}      # TODO
        self.address = address
        try:
            super().__init__(label)
        except:
            super(Device, self).__init__(label)
        # control flow stuff.
        self._set_up_daemon()
        # non-state-machine process tracking.
        self._active_threads = []
        self._active_processes = []
        # set up logging.
        self._metadata_path, self._data_path = '', ''
        self._base_path = './test_data/'
        self._data_file_extension = 'log'
        self._set_file_paths()
        # start yer daemon up.
        self.run()

    def __str__(self):
        try:
            return str(self.id)
        except:
            return 'device'
    
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
        self._add_timer('connecting', 20.0, 'CONNECT_TIMEOUT_EVENT')
        self._add_timer('disconnecting', 10.0, 'DISCONNECT_TIMEOUT_EVENT')
        return self.timers

    def _set_up_interrupts(self):
        self.interrupts = {}
        return self.interrupts

    def _set_up_requests(self):
        self._add_request('CONNECT', 'CONNECT_REQUEST_EVENT')
        self._add_request('DISCONNECT', 'DISCONNECT_REQUEST_EVENT')
        return self.requests

    # called from __init__().
    def _get_device_id(self, label):
        """
        Hunt down the device ID.
        :in: label (int) Unique ID
        :out: id (str)
        """
        # 'device' if not redefined!
        return '-'.join(['device',label])

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

    def _set_file_paths(self):
        timestamp_label = _get_time_now('label')
        self._set_metadata_path(timestamp_label)
        self._set_data_path(timestamp_label)

    def _set_metadata_path(self, timestamp_label):
        self._metadata_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                'metadata']), 'json'])

    def _set_data_path(self, timestamp_label):
        self_data_path = '.'.join([
            '_'.join([
                self._base_path+timestamp_label,
                str(self)]), self._data_file_extension])

    # process and thread management.
    def _start_process(self, target, name, args=(), kwargs={}):
        """
        Get them wheels turning.
        :in: target (*funk)
        :in: args (*)
        :in: kwargs {*}
        :out: process (Process)
        """
        process = multiprocessing.Process(target=target, args=args, kwargs=kwargs)
        process.start()
        if process.is_alive():
            self._active_processes.append(process)
            return process
        return None

    def _start_thread(self, target, name, args=(), kwargs={}):
        """
        Get them wheels turning.
        :in: target (*funk)
        :in: name (str) NOTE : set as daemon process with the word 'daemon' in here.
        :in: args (*)
        :in: kwargs {*}
        :out: thread (Thread)
        """
        thread = threading.Thread(target=target, name=name, args=args, kwargs=kwargs)
        if (name.find('daemon')) != -1:
            thread.daemon = True
        thread.start()
        if thread.isAlive():
            self._active_threads.append(thread)
            return thread
        return None

    def _kill_process(self):
        """
        Terminate all active processes broh.
        """
        _timeout = 15   # <-- Set thread termination timeout (s) here.
        _attempts = 2   # <-- Set number of attempts here.
        for attempt in range(1,_attempts+1):
            say(' '.join(['Attempt #',str(attempt),': waiting for',thread.name,'to terminate']))
            process.join([_timeout])
            if not process.is_alive():
                say(' '.join([process.name,'terminated']), 'success')
                self._active_processes.remove(process)
                return True
        return False

    def _kill_processes(self):
        """
        Terminate all active processes broh.
        """
        while len(self._active_processes) > 0:
            for process in self._active_processes:
                if not self._kill_process(process):
                    continue
        return True

    def _kill_thread(self, thread):
        """
        Terminate a thread.
        :in: thread (*Thread)
        :out: success (Bool)
        """
        _timeout = 15   # <-- Set thread termination timeout (s) here.
        _attempts = 2   # <-- Set number of attempts here.
        for attempt in range(1,_attempts+1):
            say(' '.join(['Attempt #',str(attempt),': waiting for',thread.name,'to terminate']))
            thread.join([_timeout])
            if not thread.isAlive():
                say(' '.join([thread.name,'terminated']), 'success')
                self._active_threads.remove(thread)
                return True
        return False

    def _kill_threads(self):
        """
        Terminate all active threads broh.
        """
        while len(self._active_threads) > 0:
            for thread in self._active_threads:
                if not self._kill_thread(thread):
                    continue
        return True

    def _remove_old_threads(self):
        """
        Clean self._active_threads.
        """
        for thread in self._active_threads:
            if not thread.isAlive():
                self._active_threads.remove(thread)

    def _remove_old_processes(self):
        """
        Clean self._active_processes.
        """
        for process in self._active_processes:
            if not process.is_alive():
                self._active_processes.remove(process)

    # metadata generation.
    def _fill_info(self):
        """
        Chat up the device to find where it lives as well
          as how to get into its front door.
        :in: old_info {dict} - any old metadata 'bout the device.
        """
        self.info = {
                'address': self.address,
                'id': self.id
            }

    # device-specific functionalities to be redefined.
    def _link_comms(self):
        # connect to a device.
        pass

    def _test_comms(self):
        # test communications with device.
        self._post_event('CONNECTED_EVENT')

    def _break_comms(self):
        # TODO : add test for disconnected. (not _test_comms)
        self._post_event('DISCONNECTED_EVENT')

    def _establish_connection(self, attempts=3):
        # REDEFINE : attempt to connect, test connection
        self._test_comms()
#        if attempts < 1:
#            attempts =1
#        _attempt = 1
#        while _attempt < attempts and not self._connected:
#            say('Connecting')
#            self._link_comms()
#            if self._test_comms():
#                newEvent = PriorityEvent('CONNECTED_EVENT', _MAX_PRIORITY)
#                self.event_queue.put(newEvent)
#                self._connected = True
#                say('Connected', 'success')
#                break
#            _attempt += 1
#            time.sleep(0.5)
#

    ## device-level state machine.
    def _wait_for_(self, state):
        while not self.state != state:
            time.sleep(0.1)

    def _sleep(self, this_event):
        """
        Sleeping.
        """
        if this_event == 'INIT_EVENT':
            self.printf('Sleeping...')
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
            self._establish_connection()
        elif this_event == 'CONNECT_TIMEOUT_EVENT':
            self._next_state = 'SLEEPING'
        elif this_event == 'CONNECTED_EVENT':
            self._next_state = 'STANDING_BY'
        elif this_event == 'DISCONNECT_REQUEST_EVENT':
            self._next_state = 'DISCONNECTING'
        else:
            time.sleep(0.1)

    def _disconnect(self, this_event):
        if this_event == 'INIT_EVENT':
            say('Disco nnecting...')
            self._start_timer('disconnecting')
            self._break_comms()
        elif this_event == 'DISCONNECTED_EVENT':
            self._next_state = 'SLEEPING'
        elif this_event == 'DISCONNECT_TIMEOUT_EVENT':
            say('Channel clogged; cannot disconnect', 'error')
            self._next_state = 'SLEEPING'
        else:
            time.sleep(0.3)

    def _idle(self, this_event):
        """
        Standing by.
        """
        if this_event == 'INIT_EVENT':
            say('Standing by')
        if this_event == 'DISCONNECT_REQUEST_EVENT':
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
        timestamp_label = _get_time_now('label')
        metadata_path = '_'.join([
            self._base_path+timestamp_label,
            self.id+'.json'])
        metadata_str = json.dumps(
                self.info,
                sort_keys=True,
                indent=4)
        self._write_file(metadata_path, metadata_str, 'a+')

    # state machine appendages.
    def _wait_for_ready(self, timeout=0.0):
        # TODO : add timeout too.
        self._kill_threads()
        self._kill_processes()

#
#    def _connect(self):
#        """
#        Change state here.
#        """
#        success = False
#        timeout = 10.0      # <-- Edit connection timeout / attempt here.
#        self.migrate_state('connecting')
#        attempt = 1
#        self.channel = self._link_comms()
#        _timer = self._start_thread(self._countdown, 'connecting', (timeout))
#        while 1<2:
#            # Only return success if connection confirmed.
#            if self._test_comms():
#                self.migrate_state('standing_by')
#                success = True
#                break
#            # Try again if the timer expires.
#            if not _timer.is_alive():
#                self._disconnect()
#                attempt += 1
#                if attempt > attempts:
#                    say('Failed to connect to '+str(self), 'error')
#                    self.migrate_state('sleeping')
#                    break
#                self._start_thread(self._link_comms, 'connecting')
#                _timer = self._start_thread(self._countdown, 'connecting', (timeout))
#            time.sleep(0.1)
#        return success
#        channel = None
#        try:
#            if self.interface == 'serial':
#                self.channel = Serial.serial(address)
#            elif interface == 'i2c':
#                channel = smbus.SMBus(address)
#            return channel
#        except:
#            raise Exception
#
#    def _disconnect(self):
#        """
#        Change state here.
#        """
#        raise NotImplementedError
#
#    def set_file_path(self, path_base='./test_data/'):
#        """
#        Set the base of the output path for data flow.
#        :in: path_base (str) working directory [default]
#        """
#        if not os.path.isdir(path_base):
#            say('Creating '+path_base)
#            try:
#            os.mkdir(path_base)
#            except:
#                say(''.join([
#                        'Could not create directory at ',
#                        path_base,
#                        '; using default directory']),
#                    'warning')
#                path_base = './test_data/'
#        self._base_path = path_base
#        timestamp_label = _get_time_now('label')
#        self.file_path = '.'.join([
#            '_'.join([
#                self._base_path+timestamp_label,
#                self.id]),
#            self.file_extension])
#



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
            #ddevice._wait_for_('STANDING_BY')
            time.sleep(1)
            ddevice.disconnect()

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    _test_device()

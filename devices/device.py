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
    from .control import StateMachine
    from .eventful import PriorityEvent, PriorityEventQueue
except:
    from squawk import say
    from control import StateMachine
    from eventful import PriorityEvent, PriorityEventQueue


## global declarations or something.
# event stuff.
NO_EVENT, INIT_EVENT, EXIT_EVENT, \
        COMPLETE_EVENT, CONNECTED_EVENT, DISCONNECTED_EVENT, \
        REQUEST_CONNECT_EVENT, REQUEST_DISCONNECT_EVENT, \
        TIMEOUT_CONNECTING_EVENT, \
        TIMEOUT_DISCONNECTING_EVENT = [str(i) for i in range(0,10)]
# priorities.
_MIN_PRIORITY = 0
_MAX_PRIORITY = _MIN_PRIORITY + 5
_DEFAULT_PRIORITY = _MIN_PRIORITY + 1
# time/r stuff.
_EPOCH = datetime.datetime(1970,1,1)


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


## timer class.
class Timer(object):
    """
    Vanilla timer class.
    """
    # TODO : get rid of timeout_event; add to dict of Timers.
    def __init__(self, label, duration, timeout_event='0'):
        self.label = label
        self.duration = duration
        self.timeout_event = timeout_event
        self._active_threads = []
        self._start_time = None
        self._end_time = None
        self.active = False
        self.expired = False

    def __str__(self):
        return '-'.join(['timer',str(self.label)])

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
        thread.daemon = True
        thread.start()
        if thread.isAlive():
            self._active_threads.append(thread)
            return thread
        return None

    def start(self):
        self._start_time = float(_get_time_now('epoch'))
        self._start_thread(self._countdown, 'timer')
        self.active = True

    def pause(self):
        self.active = False

    def reset(self):
        self.__init__(self.label, self.duration)

    def _countdown(self):
        while 1<2:
            if self.active:
                _time_elapsed = float(_get_time_now('epoch')) - self._start_time
                if _time_elapsed >= self.duration:
                    self.expired = True
                    self.active = False
                    break
            else:
                time.sleep(0.3)


class Device(StateMachine):
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
        self.info = {}
        self.address = address
        # set up logging.
        self._metadata_path, self._data_path = '', ''
        self._base_path = './test_data/'
        self._data_file_extension = 'log'
        self._set_file_paths()
        # control flow stuff.
        self._connected = False
        self.state = 'SLEEPING'
        self.event_queue = PriorityEventQueue()
        self.daemon = StateMachine(str(self))
        self._set_up_daemon()
        # non-state-machine process tracking.
        self._active_threads = []
        self._active_processes = []
        # initialize timers.
        self.timers = []
        self._set_up_timers()
        # start yer daemon up.
        self.daemon.run()

    def __str__(self):
        try:
            return str(self.id)
        except:
            return 'device'
    
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
        self.info = {}
        state_handlers = [
                ('SLEEPING', self._sleep),
                ('CONNECTING', self._connect),
                ('STANDING_BY', self._idle),
                ('DISCONNECTING', self._disconnect)
                ]
        for state, handler in state_handlers:
            self.daemon.add_state(state, handler)
        self.daemon.set_up(start_state=_initial_state)

    def _set_up_timers(self):
        # redefine this to add/remove timeouts.
        self._add_timer('connecting', 20.0, TIMEOUT_CONNECTING_EVENT)
        self._add_timer('disconnecting', 10.0, TIMEOUT_DISCONNECTING_EVENT)
        return self.timers


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

    # timers.
    def _add_timer(self, label, duration, timeout_event):
        # TODO : make timers a dict.
        if label in [str(timer) for timer in self.timers]:
            say('Timer '+label+' already exists', 'warning')
        else:
            newTimer = Timer(label, duration, timeout_event)
            self.timers.append(newTimer)

    def _start_timer(self, label):
        for timer in self.timers:
            if str(timer) == label:
                timer.start()
                return True
        return False

    def _reset_timers(self):
        for timer in self.timers:
            timer.reset()

    def _check_timers(self):
        for timer in self.timers:
            if timer.expired:
                # post a timeout event with max priority.
                newEvent = PriorityEvent(timer.timeout_event, _MAX_PRIORITY)
                self.event_queue.put(newEvent)
                timer.reset()


    # state machine appendages.
    def _wait_for_ready(self, timeout=0.0):
        # TODO : add timeout too.
        self._kill_threads()
        self._kill_processes()

    def migrate_state(self, n_state):
        """
        :in: n_state (str) next state
        """
        self.event_queue.clear()            # clear any outstanding events.
        self._wait_for_ready()              # wait for processes/threads to finish.
        self._reset_timers()                # reset all timeouts.
        self.daemon.set_state(n_state)      # and make the change.
        init_event = PriorityEvent(INIT_EVENT, _MAX_PRIORITY)     # NOTE : is there a better way to initialize state?
        self.event_queue.put(init_event)
        self.state = n_state


    # device-specific functionalities to be redefined.
    def _link_comms(self):
        # connect to a device.
        pass

    def _test_comms(self):
        # test communications with device.
        pass

    def _break_comms(self):
        # TODO : add test for disconnected. (not _test_comms)
        newEvent = PriorityEvent(DISCONNECTED_EVENT, _MAX_PRIORITY)
        self.event_queue.put(newEvent)

    def _establish_connection(self, attempts=3):
        # REDEFINE : attempt to connect, test connection
        _connected = True
        return _connected
        if attempts < 1:
            attempts =1
        _attempt = 1
        while _attempt < attempts and not self._connected:
            say('Connecting')
            self._link_comms()
            if self._test_comms():
                newEvent = PriorityEvent(CONNECTED_EVENT, _MAX_PRIORITY)
                self.event_queue.put(newEvent)
                self._connected = True
                say('Connected', 'success')
                break
            _attempt += 1
            time.sleep(0.5)


    ## device-level state machine.
    def _wait_for_(self, state):
        while not self.state != state:
            time.sleep(0.1)

    def _sleep(self):
        """
        Sleeping.
        """
        next_event = str(self.event_queue.get())
        print(str(next_event))
        if next_event == REQUEST_CONNECT_EVENT:
            self.migrate_state('CONNECTING')
        else:
            time.sleep(0.3)
        
    def _connect(self):
        """
        Connecting.
        """
        next_event = str(self.event_queue.get())
        # init : attempt to connect, start timeout.
        if next_event == INIT_EVENT:
            self.attempt = 1
            self._start_timer('connecting')     # <-- adjust this timeout for fine tuning.
            self._establish_connection()
        elif next_event == TIMEOUT_CONNECTING_EVENT:
            self.migrate_state('SLEEPING')
        elif next_event == CONNECTED_EVENT:
            self.migrate_state('STANDING_BY')
        elif next_event == REQUEST_DISCONNECT_EVENT:
            self.migrate_state('DISCONNECTING')
        else:
            time.sleep(0.1)

    def _disconnect(self):
        next_event = str(self.event_queue.get())
        if next_event == INIT_EVENT:
            self._start_thread(self._break_comms, 'disconnecting')
            self._start_timer('disconnecting')
        elif next_event == DISCONNECTED_EVENT:
            self.migrate_state('SLEEPING')
        elif next_event == TIMEOUT_DISCONNECTING_EVENT:
            say('Channel clogged; cannot disconnect', 'error')
            self.migrate_state('SLEEPING')
        else:
            time.sleep(0.3)

    def _idle(self):
        """
        Standing by.
        """
        next_event = str(self.event_queue.get())
        if next_event == INIT_EVENT:
            say('Standing by')
        if next_event == REQUEST_DISCONNECT_EVENT:
            self.migrate_state('DISCONNECTING')
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
        newEvent = PriorityEvent(REQUEST_CONNECT_EVENT, _DEFAULT_PRIORITY)
        self.event_queue.put(newEvent)
        print(str(self.state))

    def clean_up(self):
        """
        Close down shop.
        """
        newEvent = PriorityEvent(REQUEST_DISCONNECT_EVENT, _MAX_PRIORITY)
        self.event_queue.put(newEvent)

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

    # useful aliases.
    set_up = connect

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
            ddevice.set_up()
            ddevice._wait_for_('STANDING_BY')
            time.sleep(1)
            ddevice.clean_up()

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    _test_device()

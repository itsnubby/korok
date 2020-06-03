"""
control.py - I WILL BE IN CONTROLOLOL!
modified : 6/1/2020
     ) 0 o .
"""
import threading, multiprocessing, copy, datetime
from threading import Thread
try:        # Python3
    from .squawk import ask, say
    from .eventful import PriorityEvent, PriorityEventQueue
except:     # Python2
    from squawk import ask, say
    from eventful import PriorityEvent, PriorityEventQueue
try:
    from queue import PriorityQueue
except:
    from Queue import PriorityQueue
# for testing.
import sys, time
# TODO : add states as a dictionary with handler and events -> actions defined.

# non-blocking thread.
class NonBlockingThread(Thread):
    def __init__(self, target, name, args=(), kwargs={}):
        self._running_flag = False  # when killed by exception.
        self.stop = threading.Event()
        self.q_tip = target
        Thread.__init__(self, target=self.method_man)   # TODO : actually do this

    def method_man(self):
        try:
            while(not self.stop.wait(1)):
                self._running_flag = True
                self.q_tip()
        finally:
            self._running_flag = False

    def kill(self):
        self.stop.set()


## timer class.     TODO : move outta here.
_EPOCH = datetime.datetime(1970,1,1)
def _check_wrist(time_format='utc'):
    """
    Thanks Jon.  (;
    :in: time_format (str) ['utc','epoch']
    :out: timestamp (str)
    """
    if time_format == 'utc' or time_format == 'label':
        return datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    elif time_format == 'epoch' or time_format == 'timestamp':
        td = datetime.datetime.utcnow() - _EPOCH
        return float(td.total_seconds())
    else:
        # NOTE: Failure to specify an appropriate time_format will cost
        #         you one layer of recursion! YOU HAVE BEEN WARNED.  ) 0 o .
        return _check_wrist(time_format='epoch')


class Timer(object):
    """
    Vanilla timer class.
    """
    def __init__(self, duration):
        self.duration = duration
        self._active_threads = []
        self._start_time = None
        self._end_time = None
        self.active = multiprocessing.Value('i', 0)
        self.expired = multiprocessing.Value('i', 0)
        self._decimate = multiprocessing.Value('i', 0)

    def _start_thread(self, target, name, args=(), kwargs={}):
        """
        Get them wheels turning.
        :in: target (*funk)
        :in: name (str) NOTE : set as daemon process with the word 'daemon' in here.
        :in: args (*)
        :in: kwargs {*}
        :out: thread (Thread)
        """
        print('Starting thread, '+str(name))
        thread = threading.Thread(target=target, name=name, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        if thread.isAlive():
            self._active_threads.append(thread)
            return thread
        return None

    def set(self, duration):
        if not self.active.value > 0:
            self.duration = duration
        else:
            say('Cannot set an active timer')

    def start(self):
        self._start_thread(self._countdown, 'timer')
        self.active.value = 1
        self._decimate.value = 0

    def pause(self):
        self.active.value = 0

    def kill(self):
        self._decimate.value = 1

    def reset(self):
        self.kill()
        for _thread in self._active_threads:
            while _thread.isAlive():
                time.sleep(0.1)
                print('Waiting for thread, '+str(_thread.name))
        self.__init__(self.duration)

    def _countdown(self):
        _start_time = _check_wrist('epoch')
        self._start_time = _start_time
        while not self._decimate.value > 0:
            if self.active.value > 0:
                _current_time = _check_wrist('epoch')
                _time_elapsed = _current_time - _start_time
                if _time_elapsed >= self.duration:
                    self.expired.value = 1
                    break
            else:
                _start_time = _check_wrist('epoch') # need to re-adjust start time when paused.
                time.sleep(0.3)
        self.active.value = 0
        self._end_time = _check_wrist('epoch')
        print('Timer thread ended')

    def is_expired(self):
        if self.expired.value > 0:
            return True
        return False

## globalization.
class StateMachine(object):
    """
    Controller using a finite state machine.
    """
    def __init__(self, label):
        self.label = str(label)
        # state machine jazz.
        self.handlers = {}
        self.state = None
        self._next_state = None
        self.available_states = [] 
        # management stuff.
        self._active_threads = []
        self._active_processes = []

    def __str__(self):
        return self.label

    def printf(self, prompt, flag=''):
        say(str(self)+' : '+prompt, flag)

    ## helper functions.
    # process and thread management.
    def _start_process(self, target, name, args=(), kwargs={}):
        """
        Get them wheels turning.
        :in: target (*funk)
        :in: args (*)
        :in: kwargs {*}
        :out: process (Process)
        """
        print('Starting process, '+str(name))
        process = multiprocessing.Process(target=target, args=args, kwargs=kwargs)
        process.daemon = True
        process.start()
        if process.is_alive():
            self._active_processes.append(process)
        return process

    def _start_thread(self, target, name, args=(), kwargs={}):
        """
        Get them wheels turning.
        :in: target (*funk)
        :in: name (str)
        :in: args (*)
        :in: kwargs {*}
        :out: thread (Thread)
        """
        print('Starting thread, '+str(name))
        thread = threading.Thread(target=target, name=name, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        if thread.isAlive():
            self._active_threads.append(thread)
            return thread
        return None

    def _kill_process(self, process):
        """
        Terminate all active processes broh.
        """
        process.terminate()
        process.join()
        if not process.is_alive():
            self._active_processes.remove(process)
            print('Ending process, '+str(process.name))

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
            self.printf(' '.join(['Attempt #',str(attempt),': waiting for',thread.name,'to terminate']))
            thread.join()
            if not thread.isAlive():
                self.printf(' '.join([thread.name,'terminated']), 'success')
                self._active_threads.remove(thread)
                print('Ending thread, '+str(process.name))
                return True
        return False

    def _kill_threads(self):
        """
        Terminate all active threads broh.
        """
        while len(self._active_threads) > 0:
            for thread in self._active_threads:
                if not self._kill_thread(thread) or thread.name.find('daemon'):
                    continue
        return True

    def _remove_old_threads(self):
        """
        Clean self._active_threads.
        """
        for thread in self._active_threads:
            if not thread.isAlive():
                self.printf('Removing thread, '+thread.name)
                self._active_threads.remove(thread)

    def _remove_old_processes(self):
        """
        Clean self._active_processes.
        """
        for process in self._active_processes:
            if not process.is_alive():
                self._active_processes.remove(process)

    def _run(self):
        self.printf('Starting up '+str(self))
        while 1<2:
            self.handlers[self.state]()

    ## public functions.
    def add_state(self, name, handler):
        name = name.upper()
        self.handlers[name] = handler
        if not name in self.available_states:
            self.available_states.append(name)
    
    def migrate_state(self):
        self.state = self._next_state

    def set_up(self, start_state=None):
        if not start_state:
            start_state = ask('Initial state for '+self.label+' : ', answer_type=str)
        self._next_state = start_state.upper()
        self.migrate_state()
    
    def run(self):
        if not self.state:
            self.printf('Please call \'set_up\' method before starting state machine')
            return
        self._start_thread(self._run, '-'.join([str(self),'daemon']))


## Events/Services State Machine:
# priorities.
_MAX_PRIORITY = 0
_MIN_PRIORITY = _MAX_PRIORITY + 5
_DEFAULT_PRIORITY = _MAX_PRIORITY + 1

class ESMachine(StateMachine):
    """
    REDEFINE : _update(); ADD : state handlers
    FSM with Events.
    """
    def __init__(self, label):
        try:
            super().__init__(label)
        except:
            super(ESMachine, self).__init__(label)
        # shared space.
        self.flags = {}     # {flag_name: mp.Value}
        # event inits.
        self.current_time = 0.0     # time in Epoch secs.
        self.events = {}
        self._set_up_events()
        self.event_queue = PriorityEventQueue()
        # timer inits.
        self.timers = {}
        self._set_up_timers()
        self._active_timer_names = []
        # interrupt inits.
        self.interrupts = {}
        self._set_up_interrupts()
        self._incoming_interrupts = PriorityQueue()
        # user request inits.
        self.requests = {}
        self._set_up_requests()
        self._incoming_requests = PriorityQueue()

    def _check_wrist(self, time_format='utc'):
        # TODO : update current time.
        """
        :in: time_format (str) ['utc','epoch']
        :out: timestamp (str)
        """
        if time_format == 'utc' or time_format == 'label':
            return datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        elif time_format == 'epoch' or time_format == 'timestamp':
            td = datetime.datetime.utcnow() - _EPOCH
            return float(td.total_seconds())
        else:
            # NOTE: Failure to specify an appropriate time_format will cost
            #         you one layer of recursion! YOU HAVE BEEN WARNED.  ) 0 o .
            return _check_wrist(time_format='epoch')


    # to be redefined.
    def _set_up_events(self):
        # REDEFINE : this is where you _add_event(s)
        self._add_event('NO_EVENT', 0)
        self._add_event('INIT_EVENT', 2)

    def _set_up_timers(self):
        # REDEFINE : this is where you _add_timer(s)
        pass

    def _set_up_interrupts(self):
        # REDEFINE : this is where you _add_interrupt(s)
        pass

    def _set_up_requests(self):
        # REDEFINE : this is where you _add_request(s)
        pass
    
    # events.
    def _add_event(self, event_name, priority):
        newEvent = PriorityEvent(event_name, priority)
        self.events[event_name] = newEvent

    # timers.
    def _add_timer(self, label, duration, timeout_event_name):
        newTimer = Timer(duration)
        self.timers[label] = {}
        self.timers[label] = {
                'timer': newTimer,
                'timeout_event_name': timeout_event_name
                }

    def _set_timer(self, label, duration):
        try:
            _duration = float(copy.deepcopy(duration))
            self.timers[label]['timer'].set(_duration)
        except:
            self.printf('Could not set timer')

    def _start_timer(self, label):
        try:
            self.timers[label]['timer'].start()
            self._active_timer_names.append(label)
            return True
        except:
            self.printf('Cannot start timer; timer '+label+' not added')
            return False

    # requests.
    def _add_request(self, label, request_event_name=''):
        if not request_event_name:
            request_event_name = label
        self.requests[label] = request_event_name

    # interrupts.
    def _add_interrupts(self):
        pass
    
    # flags.
    def add_flag(self, name):
        if not name in self.flags.keys():
            self.flags[name] = multiprocessing.Value('i',0)   
        
    def set_flag(name, value):
        # value: Boolean
        if not value:
            value = 0
        else:
            value = 1
        try:
            self.flags[name] = value
        except:
            self.printf('Could not set flag, '+str(flag)+' to '+str(value))

    # resetters.
    def _reset_timers(self):
        for timer_name in self._active_timer_names:
            self.timers[timer_name]['timer'].reset()
            self._active_timer_names.remove(timer_name)

    def _clear_interrupts(self):
        while not self._incoming_interrupts.empty():
            self._incoming_interrupts.get()

    def _clear_requests(self):
        while not self._incoming_requests.empty():
            self._incoming_requests.get()

    # checkers.
    def _check_timers(self):
        for timer_name in self._active_timer_names:
            if self.timers[timer_name]['timer'].is_expired():
                # post a timeout event, reset timer, remove from active timers.
                self._post_event(self.timers[timer_name]['timeout_event_name'])
                self.timers[timer_name]['timer'].reset()
                self._active_timer_names.remove(timer_name)

    def _check_interrupts(self):
        while not self._incoming_interrupts.empty():
            _next_interrupt = self._incoming_interrupts.get()[1]
            _interrupt_name = '_'.join([_next_interrupt, 'INTERRUPT_EVENT'])
            self._post_event(_interrupt_name)

    def _check_requests(self):
        while not self._incoming_requests.empty():
            _next_request = self._incoming_requests.get()[1]
            _request_name = '_'.join([_next_request, 'REQUEST_EVENT'])
            self._post_event(_request_name)

    # state machine enhancements.
    def _post_event(self, event_name):
        try:
            event = self.events[event_name]
            self.event_queue.put(event)
        except TypeError:
            # too many requests coming in at the same time.
            pass
        except:
            self.printf('Cannot post unsupported event : '+str(event_name), 'error')

    def _get_event(self):
        event = str(self.event_queue.get())
        return event

    def migrate_state(self):
        self.event_queue.clear()            # clear any outstanding events.
        self._reset_timers()                # reset all timeouts.
        self._kill_processes()
        self.state = self._next_state
        self._post_event('INIT_EVENT')

    # main loop.
    def _update(self):
        self._check_interrupts()
        self._check_timers()
        self._check_requests()
        self._remove_old_threads()
        self._remove_old_processes()
        if self.state != self._next_state and self._next_state in self.available_states:
            self.migrate_state()
        self.current_time = self._check_wrist('epoch')

    def _run(self):
        self.printf('Starting up'+str(self))
        while 1<2:
            event_name = self._get_event()
            self.handlers[self.state](event_name)
            self._update()

## tests.
def _the_sleepy_handler():
    print('I like milk!')
    time.sleep(0.4)

def _the_killer():
    print('Let the milk spoil...')
    sys.exit(1)

def _test_control():
    _initial_state = 'SLEEPING'
    # tests.
    nublette = StateMachine('nub')
    nublette.add_state('sleeping', _the_sleepy_handler)
    nublette.add_state('killing', _the_killer)
    nublette.set_up(start_state=_initial_state)
    nublette.run()
    while 1<2:
        time.sleep(5)
        nublette.set_state('killing')

def _nublette():
    while 1<2:
        print('Hi nub.')
        time.sleep(1)

def _test_nbts():
    nub = NonBlockingThread(_nublette, 'nub')
    nub.start()
    time.sleep(4)
    print('git lit')
    nub.kill()
    nub.join()
    print('Goodonya')

def _test_timers():
    nublord = ESMachine()

if __name__ == '__main__':
    #_test_nbts()
    #_test_control()
    _test_timers()

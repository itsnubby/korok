"""
control.py - I WILL BE IN CONTROLOLOL!
modified : 5/11/2020
     ) 0 o .
"""
import threading, multiprocessing
try:        # Python3
    from .devices.squawk import ask, say
except:     # Python2
    from devices.squawk import ask, say
# for testing.
import sys, time
# TODO : add states as a dictionary with handler and events -> actions defined.

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
        self.available_states = [] 
        # management stuff.
        self._active_threads = []
        self._active_processes = []

    def __str__(self):
        return self.label

    def printf(self, prompt, flag=''):
        say(str(self)+' : '+prompt)

    ## helper functions.
    def _start_thread(self, target, name, args=(), kwargs={}):
        """
        Get them wheels turning.
        :in: target (*funk)
        :in: name (str)
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

    def _run(self):
        self.printf('Starting up')
        while 1<2:
            self.handlers[self.state]()

    ## public functions.
    def add_state(self, name, handler):
        name = name.upper()
        self.handlers[name] = handler
        if not name in self.available_states:
            self.available_states.append(name)
    
    def migrate_state(self, next_state):
        next_state = next_state.upper()
        if next_state in self.available_states:
            self.state = next_state
        else:
            self.printf('Cannot enter state, '+start_state+'; please add with handler first')

    def set_up(self, start_state=None):
        if not start_state:
            start_state = ask('Initial state for '+self.label+' : ', answer_type=str)
        self.migrate_state(start_state)
    
    def run(self):
        if not self.state:
            self.printf('Please call \'set_up\' method before starting state machine')
            return
        self._start_thread(self._run, '-'.join([str(self),'daemon']))


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
        nublette.migrate_state('killing')

if __name__ == '__main__':
    _test_control()

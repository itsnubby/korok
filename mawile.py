"""
mawile.py - the data collector daemon and USER interface.
modified : 6/1/2020
     ) 0 o .
"""
import sys
try:
    from .sableye import find_devices
    from .devices.control import ESMachine
except:
    from sableye import find_devices
    from devices.control import ESMachine


# event stuff.
_MAX_PRIORITY = 0
_MIN_PRIORITY = _MAX_PRIORITY + 5
_DEFAULT_PRIORITY = _MAX_PRIORITY + 1
# timeouts.
_SETUP_TIMEOUT = 10.0

class Mawile(ESMachine):
    def __init__(self):
        label = 'mawile-daemon'
        try:
            super().__init__(label)
        except:
            super(Mawile, self).__init__(label)
        self.add_flag('ready')
        self.sensors = []
        self.controllers = []
        self.mech = []

    def _set_up_events(self):
        self._add_event('NO_EVENT', _MIN_PRIORITY)
        self._add_event('INIT_EVENT', _MAX_PRIORITY)
        self._add_event('EXIT_EVENT', _MIN_PRIORITY)
        self._add_event('COMPLETE_EVENT', _MAX_PRIORITY)
        self._add_event('SETUP_TIMEOUT_EVENT', _MIN_PRIORITY)
        self._add_event('_EVENT', _MIN_PRIORITY)

    def _set_up_timers(self):
        # redefine this to add/remove timeouts.
        self._add_timer('setup', _SETUP_TIMEOUT, 'SETUP_TIMEOUT_EVENT')
        return self.timers

    def _set_up_daemon(self):
        _initial_state = 'SLEEPING'
        state_handlers = [
                ('SETTING_UP', self._run_setup),
                ('COLLECTING_DATA', self._run_collect_data),        # Python was a bad choice for an ES framework, R.I.P.
                ('CLEANING_UP', self._run_clean_up)
                ]
        for state, handler in state_handlers:
            self.add_state(state, handler)
        self.set_up(start_state=_initial_state)
        
    def _check_setup_progress(self):
        if self.flags['ready']:
            self._post('COMPLETE_EVENT')

    def _run_setup(self, this_event):
        if this_event == 'INIT_EVENT':
            self._start_process(self.setup, 'setting_up')
            self._start_timer('setup')
        elif this_event == 'SETUP_TIMEOUT_EVENT':
            self.printf('Could not set up! Exiting', 'error')
            sys.exit()
        elif this_event == 'COMPLETE_EVENT':
            self.printf('Setup complete', 'success')
            self._next_state = 'COLLECTING_DATA'
        else:
            time.sleep(0.3)
            self._check_setup_progress()

    def _check_dc_progress(self):
        for sensor in self.sensors:
            if not sensor.state == 'STANDING_BY':
                return
        self._post_event('COMPLETE_EVENT')

    def _run_data_collection(self, this_event):
        if this_event == 'INIT_EVENT':
            self._start_process(self.collect_data)
        elif this_event == 'COMPLETE_EVENT':

            self.set_flag('ready', True)
            self.printf('Data collection complete')
            self._next_state = 'CLEANING_UP'
        else:
            time.sleep(0.3)
            self._check_dc_progress()

    def _check_clean_up_progress(self):
        for device in self.devices:
            if not device.state == 'SLEEPING':
                return
        self._post_event('COMPLETE_EVENT')

    def _run_clean_up(self, this_event):
        if this_event == 'INIT_EVENT':
            self._start_process(self.clean_up)
        elif this_event == 'COMPLETE_EVENT':
            self.printf('Hasta luego.  ) 0 o .')
            sys.exit()
        else:
            time.sleep(0.3)
            self._check_clean_up_progress()

    def setup(self):
        # find and connect to all available devices.
        self.sensors, self.controllers, self.mech = find_devices()
        self.devices = self.sensors + self.controllers + self.mech
        for device in self.devices:
            device.connect()
        # TODO : make sure that devices are connected.
        self.set_flag('ready', True)


    def collect_data(self):
        # TODO : make this a thing.
        self.set_flag('ready', False)
        for sensor in self.sensors:
            sensor.start_recording(10)

    def clean_up(self, this_event):
        try:
            for device in self.devices:
                device.clean_up()
        except KeyboardInterrupt:
            sys.exit()


def _mawile():
    """
    chomp down on some data.
    """
    mawile = Mawile()

if __name__ == "__main__":
    _mawile()

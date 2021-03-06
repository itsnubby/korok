"""
eventful.py - Events and shuz.
modified : 5/12/2020
     ) 0 o .
"""
try:
    from queue import PriorityQueue
except:
    from Queue import PriorityQueue


class Event(object):
    def __init__(self, label):
        self.label = str(label)

    def __str__(self):
        return self.label

    def __int__(self):
        return self.priority

class PriorityEvent(Event):
    """
    Generic event class.
    :in: priority (int) lowest = 0, highest = TBD
    """
    def __init__(self, label, priority=0):
        self.priority = int(priority)
        try:
            super().__init__(label)
        except:
            super(PriorityEvent, self).__init__(label)

class EventQueue(object):
    def __init__(self):
        self.events = PriorityQueue()

    def __str__(self):
        return str(self.events)

    def put(self, event, priority=0):
        self.events.put_nowait((priority, event))

    def get(self):
        return self.events.get_nowait()[1]

    def empty(self):
        return self.events.empty()

    def clear(self):
        while not self.empty():
            self.get()

class PriorityEventQueue(EventQueue):
    def put(self, p_event):
        try:
            super().put(p_event, priority=int(p_event))
        except:
            super(PriorityEventQueue, self).put(p_event, priority=int(p_event))


## tests.
def _test_eventful():
    _MIN_PRIORITY = 0
    _DEFAULT_PRIORITY = 1
    _MID_PRIORITY = 5
    _MAX_PRIORITY = 10

    # events.
    thingle = PriorityEvent('test1', _DEFAULT_PRIORITY)
    thinglar = PriorityEvent('test2', _MIN_PRIORITY)
    thingwad = PriorityEvent('test3', _MID_PRIORITY)
    thinglad = PriorityEvent('test4', _MAX_PRIORITY)
    thing = PriorityEventQueue()

    # testing.
    print('PEQ : '+str(thing))
    thing.put(thingle)
    thing.put(thinglar)
    thing.put(thinglad)
    thing.put(thingwad)
    print('PEQ after putting stuff : '+str(thing))
    while not thing.empty():
        reclaimed = thing.get()
        print(str(int(reclaimed))+'. '+str(reclaimed))
    print('All tested.')


if __name__ == '__main__':
    _test_eventful()


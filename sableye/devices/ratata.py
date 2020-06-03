#    ) 0 o .
import time, threading
from threading import Thread

class BlockingTestThread(Thread):
    def __init__(self):
        self._running_flag = False
        self.stop  = threading.Event()
        Thread.__init__(self, target=self.test_method)

    def test_method(self):
        try:
            while(not self.stop.wait(1)):
                self._running_flag = True
                print 'Start wait'
                self.stop.wait(100)
                print 'Done waiting'
        finally:
                self._running_flag = False

    def terminate(self):
         self.stop.set()  

if __name__ == "__main__":
    thread = BlockingTestThread()
    thread.start()

    time.sleep(2)
    print 'Time sleep 2'
    thread.terminate()
    print("Terminated.")
    time.sleep(1)
    print "Joining thread"
    thread.join()
    print "Done Joining thread"

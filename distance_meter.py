from threading import Thread
from eventhandler import EventHandler
from time import sleep, time, time_ns
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO_TRIGGER = 23
GPIO_ECHO = 24
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

# Ignore small changes
INACCURACY = 2


class DistanceMeter(Thread):
    """
    Measures the disctance using the echo sensor and throws an event if the direction changes.
    """

    # Store longest/shortest distance and the time it was measured
    distance = 0
    last_time = 0
    # Is the Thread running?
    running = False
    # To save the current direction
    forward = False
    # Only fire event when more direction changes are detected, to handle wrong numbers
    new_direction_count = 0

    def __init__(self):
        self.event_handler = EventHandler('r_f', 'r_b')
        Thread.__init__(self)

    def start_meter(self):
        """Starts the distance meter"""
        self.running = True
        self.start()

    def stop_meter(self):
        """Stops the distance meter"""
        self.running = False
        self.join()

    def get_distance(self):
        """Gets the distance from the echo sensor"""
        GPIO.output(GPIO_TRIGGER, GPIO.HIGH)
        sleep(0.00001)
        GPIO.output(GPIO_TRIGGER, GPIO.LOW)

        pulse_start_time = time()
        pulse_end_time = time()
        while GPIO.input(GPIO_ECHO) == 0:
            pulse_start_time = time()

        while GPIO.input(GPIO_ECHO) == 1:
            pulse_end_time = time()

        pulse_duration = pulse_end_time - pulse_start_time
        d = round(pulse_duration * 17150, 2)
        #print("%s", d)
        return d

    def run(self):
        """
        Until the Thread is stopped, the distance is measured and the event is thrown when the direction changes.

        Possible events are:
        r_f: forward
        r_b: backward

        The event contains also the distance and the time of the direction change.
        """
        while self.running:
            d = self.get_distance()

            # Ignore unvalid values
            if d > 300:
                continue

            if self.forward:
                # Store new distance if the value is greater
                if d > self.distance:
                    self.distance = d
                    self.new_direction_count = 0
                    self.last_time = time_ns()
                elif d < (self.distance - INACCURACY):
                    # It seems it is going into the other direction
                    # but to handle incorrect numbers, we only fire the event if the 3rd value is smaller
                    if self.new_direction_count < 2:
                        #print('r_b: %s', self.new_direction_count)
                        self.new_direction_count = self.new_direction_count + 1
                    else:
                        #print('>>> r_b %s', self.distance)
                        self.new_direction_count = 0
                        self.event_handler.fire('r_b', self.distance, self.last_time)
                        self.forward = False
                        self.distance = d
            else:
                if d < self.distance:
                    self.distance = d
                    self.new_direction_count = 0
                    self.last_time = time_ns()
                elif d > (self.distance + INACCURACY):
                    if self.new_direction_count < 2:
                        #print('r_f: %s', self.new_direction_count)
                        self.new_direction_count = self.new_direction_count + 1
                    else:
                        #print('>>> r_f %s', self.distance)
                        self.new_direction_count = 0
                        self.event_handler.fire('r_f', self.distance, self.last_time)
                        self.forward = True
                        self.distance = d

            # Wait a bit before next measurement
            sleep(0.1)

from distance_meter import DistanceMeter
from flask import Flask, Response, render_template
from time import time_ns
import queue
import json
import numpy as np

FACTOR_DISTANCE = 0.149
"""The factor to multiply the distance with to get the appr. distance of a stroke"""
MIN_STROKE_DISTANCE = 0.4
"""Used to prevent unlogic distance changes"""
NANO_TO_SECOND = 1000000000


class Rower:
    """
    Central class for the RP Rower. It runs a Web Server to provide the rower UI.
    It listens to the events thrown by distance_meter.py.
    """

    def __init__(self):
        self.dm = DistanceMeter()
        self.dm.event_handler.link(self.direction_change_f, 'r_f')
        self.dm.event_handler.link(self.direction_change_b, 'r_b')
        self.start_forward_distance = self.dm.get_distance()
        self.start_forward_time = 0
        self.start_backward_time = 0
        self.distance = 0
        self.total_strokes = 0
        self.total_distance = 0.000001
        self.strokes = []
        self.start_time = time_ns()
        self.running = False

    def start(self):
        """Start the rower"""
        self.dm.start_meter()
        self.running = True
        self.start_forward_time = time_ns()
        announcer.announce(msg=f'data: {"{}"}\n\n')

    def stop(self):
        """Stop the rower"""
        self.dm.stop_meter()
        self.running = False

    def direction_change_f(self, distance, time_in_ns):
        """
        Handling the forward direction change.
        The values are calculated and the event is added to queue to be send to the connection the client can open with the listen endpoint.
        """

        if self.distance < MIN_STROKE_DISTANCE:
            print("Ignore this stroke with distance:", self.distance)
            self.start_forward_distance = self.dm.get_distance()
            return

        # Store the values from the stroke
        self.total_strokes += 1
        t_forward = round((self.start_backward_time - self.start_forward_time) / NANO_TO_SECOND, 3)
        t_backward = round((time_in_ns - self.start_backward_time) / NANO_TO_SECOND, 3)
        # stroke | distance | time forward | time backward
        self.strokes.append([self.total_strokes, self.distance, t_forward, t_backward])

        # Add latest data to the queue and
        # event expects data field and two line breaks
        announcer.announce(msg=f'data: {json.dumps(self.calculate_data(t_forward, t_backward))}\n\n')

        # Collect values for the next stroke
        self.start_forward_distance = distance
        self.start_forward_time = time_in_ns

    def direction_change_b(self, distance, time_in_ns):
        """Handling the backward direction change. Just some values are stored"""
        self.start_backward_time = time_in_ns
        self.distance = (distance - self.start_forward_distance) * FACTOR_DISTANCE
        # In case something weird happens, we don't want to have a negative distance
        if self.distance < 0:
            self.distance = 0

    def calculate_data(self, t_forward, t_backward):
        """Caluclate the different metrics based on the numbers and return an JSON object with the values"""
        self.total_distance = self.total_distance + self.distance
        total_time = (time_ns() - self.start_time) / NANO_TO_SECOND
        # Caluclate the SPM + 500m avg on the last 5 strokes
        last_5_numbers = np.sum(self.strokes[-5:], axis=0)
        last_5_total_distance = last_5_numbers[1]
        last_5_total_time = last_5_numbers[2] + last_5_numbers[3]
        l = 5 if len(self.strokes) > 5 else len(self.strokes)

        # Prepare the event data
        d = {
            'total_distance': round(self.total_distance, 1),
            'total_time': sec_to_min(total_time),
            'total_strokes': self.total_strokes,
            'last_stroke_forward': round(t_forward, 1),
            'last_stroke_backward': round(t_backward, 1),
            'last_stroke_total': round(t_forward + t_backward, 1),
            'last_stroke_distance': round(self.distance, 1),
            # e.g. 155.9 secs = 20 Strokes, 60 secs = n Strokes
            'spm': round(l / last_5_total_time * 60, 1),
            'average_spm': round(self.total_strokes / total_time * 60, 1),
            # e.g. 760m = 150 secs, 500m = n secs
            'time_500m': sec_to_min(last_5_total_time / last_5_total_distance * 500),
            'average_500m': sec_to_min(total_time / self.total_distance * 500),
            'running': self.running
        }
        print("Distance:", self.distance)
        return d


def sec_to_min(sec):
    """Convert seconds to minutes"""
    return str(int(sec / 60)) + ":" + str(int(sec % 60)).zfill(2)


class MessageAnnouncer:
    """
    Events are stored in a queue. The queue is filled by the rower class. The events are stream to the client. 
    """

    def __init__(self):
        self.listeners = []

    def listen(self):
        self.listeners.append(queue.Queue(maxsize=5))
        return self.listeners[-1]

    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]


app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    """Get the UI"""
    return render_template("overview.html")


@app.route('/start', methods=['GET'])
def start():
    """Endpoin to start the rower"""
    global rower
    if rower is not None and rower.running:
        print("Rower is already running")
    else:
        rower = Rower()
        rower.start()
    return {}, 200


@app.route('/stop', methods=['GET'])
def stop():
    """Endpoint to stop the rower"""
    global rower
    rower.stop()
    return {}, 200


@app.route('/listen', methods=['GET'])
def listen():
    """Endpoint to get the stream to update the UI with the latest numbers"""
    def stream():
        messages = announcer.listen()
        while True:
            msg = messages.get()
            yield msg

    return Response(stream(), mimetype='text/event-stream')


try:
    announcer = MessageAnnouncer()
    rower = None
    app.run(debug=False, host='0.0.0.0')

finally:
    rower.dm.stop_meter()
    print("Stop Rower")

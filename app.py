from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)

class TrafficEnvironment:
    def __init__(self):
        self.reset()

    def _initial_counts(self):
        return {
            "North": random.randint(1, 5),
            "South": random.randint(1, 5),
            "East": random.randint(1, 5),
            "West": random.randint(1, 5),
        }

    def _choose_next_lane(self):
        max_count = max(self.counts.values())
        top_lanes = [lane for lane, count in self.counts.items() if count == max_count]
        return random.choice(top_lanes)

    def _green_time(self, lane):
        count = self.counts[lane]
        # Keep green times realistic between 10 and 20 seconds
        return min(20, max(10, count * 2))

    def reset(self):
        self.step = 1
        self.phase = "GREEN"
        self.waiting_time = 0
        self.counts = self._initial_counts()
        self.active_lane = self._choose_next_lane()
        self.remaining_time = self._green_time(self.active_lane)

    def _update_waiting_time(self):
        for lane, count in self.counts.items():
            if lane != self.active_lane:
                self.waiting_time += count

    def _simulate_new_traffic(self):
        new_counts = {}

        for lane, count in self.counts.items():
            if lane == self.active_lane:
                # Cars passed through, maybe a new one trickles in
                new_counts[lane] = random.randint(0, 1)
            else:
                # Cars pile up at the red lights
                new_counts[lane] = count + random.randint(1, 4)

        self.counts = new_counts

    def next_step(self):
        self.step += 1
        self._update_waiting_time()
        self._simulate_new_traffic()
        self.active_lane = self._choose_next_lane()
        self.phase = "GREEN"
        self.remaining_time = self._green_time(self.active_lane)

    def get_data(self):
        return {
            "step": self.step,
            "active_lane": self.active_lane,
            "active_directions": self.active_lane,
            "phase": self.phase,
            "remaining_time": self.remaining_time,
            "waiting_time": self.waiting_time,
            "camera_counts": self.counts,
            "sensor_counts": self.counts,
        }

env = TrafficEnvironment()

@app.route("/")
def home():
    return render_template("index.html", data=env.get_data())

@app.route("/next_step")
def next_step():
    env.next_step()
    return jsonify(env.get_data())

@app.route("/reset")
def reset():
    env.reset()
    return jsonify(env.get_data())

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

class TrafficEnvironment:
    def __init__(self):
        self.reset()

    def reset(self):
        self.step = 1
        self.phase = "GREEN"
        self.active_lane = "North"
        self.remaining_time = 10
        self.counts = {"North": 0, "South": 0, "East": 0, "West": 0}
        self.waits = {"North": 0, "South": 0, "East": 0, "West": 0}

    def next_step(self, counts, waits):
        self.step += 1
        self.counts = counts
        self.waits = waits
        
        # =========================================================
        # REAL-TIME AI LOGIC: MAX-PRESSURE CONTROL
        # =========================================================
        # Find the lane with the highest accumulated wait time
        max_wait = max(self.waits.values())
        
        if max_wait > 0:
            # Pick the lane with the most suffering cars!
            top_lanes = [lane for lane, wait in self.waits.items() if wait == max_wait]
            self.active_lane = random.choice(top_lanes)
        else:
            # If no one is waiting, just pick a lane with cars
            max_count = max(self.counts.values())
            if max_count > 0:
                top_lanes = [lane for lane, count in self.counts.items() if count == max_count]
                self.active_lane = random.choice(top_lanes)

        self.phase = "GREEN"
        
        # Give them enough time to clear the cars that are there
        target_count = self.counts[self.active_lane]
        self.remaining_time = min(20, max(8, target_count * 2))

    def get_data(self):
        return {
            "step": self.step,
            "active_lane": self.active_lane,
            "active_directions": self.active_lane,
            "phase": self.phase,
            "remaining_time": self.remaining_time
        }

env = TrafficEnvironment()

@app.route("/")
def home():
    return render_template("index.html", data=env.get_data())

@app.route("/next_step")
def next_step():
    # Read the real-time CV Tracking data sent from the browser!
    waits = {
        "North": request.args.get('nw', default=0, type=int),
        "South": request.args.get('sw', default=0, type=int),
        "East": request.args.get('ew', default=0, type=int),
        "West": request.args.get('ww', default=0, type=int)
    }
    counts = {
        "North": request.args.get('nc', default=0, type=int),
        "South": request.args.get('sc', default=0, type=int),
        "East": request.args.get('ec', default=0, type=int),
        "West": request.args.get('wc', default=0, type=int)
    }
    
    env.next_step(counts, waits)
    return jsonify(env.get_data())

@app.route("/reset")
def reset():
    env.reset()
    return jsonify(env.get_data())

if __name__ == "__main__":
    app.run(debug=True)
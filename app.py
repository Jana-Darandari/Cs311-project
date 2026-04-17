import os
from collections import deque
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
# Load simple config from environment
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-for-local')


LANES = ("North", "South", "East", "West")


class TrafficAgent:
    """A simple observe-think-act traffic agent with short-term memory."""

    def __init__(self):
        self.history = deque(maxlen=12)
        self.observation_history = deque(maxlen=20)
        self.starvation = {lane: 0 for lane in LANES}
        self.last_decision = {
            "lane": "North",
            "duration": 10,
            "score": 0,
            "raw_score": 0,
            "reason": "Initial startup state.",
            "pressure": {lane: 0 for lane in LANES},
            "dominant_lane": "North",
        }

    def reset(self):
        self.history.clear()
        self.observation_history.clear()
        self.starvation = {lane: 0 for lane in LANES}
        self.last_decision = {
            "lane": "North",
            "duration": 10,
            "score": 0,
            "raw_score": 0,
            "reason": "Agent reset to default state.",
            "pressure": {lane: 0 for lane in LANES},
            "dominant_lane": "North",
        }

    def observe(self, counts, waits, active_lane, step):
        total_wait = sum(waits.values())
        total_cars = sum(counts.values())
        pressure = {
            lane: waits[lane] * 2 + counts[lane] + self.starvation[lane] * 3
            for lane in LANES
        }
        dominant_lane = max(
            LANES,
            key=lambda lane: (pressure[lane], waits[lane], counts[lane])
        )
        avg_wait = round(total_wait / total_cars, 2) if total_cars else 0

        state = {
            "step": step,
            "counts": counts.copy(),
            "waits": waits.copy(),
            "active_lane": active_lane,
            "total_wait": total_wait,
            "total_cars": total_cars,
            "avg_wait": avg_wait,
            "recent_lanes": [entry["lane"] for entry in self.history],
            "starvation": self.starvation.copy(),
            "pressure": pressure,
            "dominant_lane": dominant_lane,
        }
        self.observation_history.append(
            {
                "step": step,
                "total_wait": total_wait,
                "total_cars": total_cars,
                "avg_wait": avg_wait,
            }
        )
        return state

    def generate_actions(self, state):
        actions = []
        for lane in LANES:
            lane_count = state["counts"][lane]
            lane_wait = state["waits"][lane]
            starvation = state["starvation"][lane]
            base_duration = 8 + min(12, lane_count * 2 + min(6, lane_wait))
            duration = min(20, max(6, base_duration + min(4, starvation)))
            actions.append({"lane": lane, "duration": duration})
        return actions

    def score_action(self, state, action):
        lane = action["lane"]
        counts = state["counts"]
        waits = state["waits"]
        starvation = state["starvation"]
        pressure = state["pressure"]

        same_lane_penalty = 6 if lane == state["active_lane"] else 0
        empty_lane_penalty = 15 if counts[lane] == 0 and waits[lane] == 0 else 0
        idle_intersection_penalty = 10 if state["total_cars"] == 0 else 0

        pressure_score = waits[lane] * 5
        demand_score = counts[lane] * 3
        starvation_score = starvation[lane] * 4
        lane_pressure_bonus = pressure[lane] * 1.5

        opposing_pressure = sum(
            waits[other] * 2 + counts[other]
            for other in LANES
            if other != lane
        )

        recent_bonus = 0
        if self.history and self.history[-1]["lane"] != lane:
            recent_bonus = 2

        score = (
            pressure_score
            + demand_score
            + starvation_score
            + lane_pressure_bonus
            + recent_bonus
            - same_lane_penalty
            - empty_lane_penalty
            - idle_intersection_penalty
            - opposing_pressure * 0.1
        )

        return round(score, 2)

    def normalize_score(self, scored_actions, best_score):
        """Convert the internal score into a relative 0-100 display value."""
        scores = [score for _, score in scored_actions]
        if not scores:
            return 0.0

        high = max(scores)
        low = min(scores)
        spread = max(1.0, high - low)

        sorted_scores = sorted(scores, reverse=True)
        second_best = sorted_scores[1] if len(sorted_scores) > 1 else low

        relative_strength = (best_score - low) / spread
        decision_gap = max(0.0, best_score - second_best) / spread

        # Keep the display score readable and dynamic instead of clustering near 100.
        display_score = (relative_strength * 60) + (decision_gap * 40)
        return round(min(95.0, max(5.0, display_score)), 1)

    def choose_action(self, state):
        actions = self.generate_actions(state)
        scored_actions = [
            (action, self.score_action(state, action))
            for action in actions
        ]
        best_action, best_score = max(
            scored_actions,
            key=lambda item: (item[1], state["waits"][item[0]["lane"]], state["counts"][item[0]["lane"]])
        )

        lane = best_action["lane"]
        lane_wait = state["waits"][lane]
        lane_count = state["counts"][lane]
        lane_starvation = state["starvation"][lane]

        if lane_wait > 120:
            reason = f"{lane} has the heaviest congestion right now, so the agent is giving it priority."
        elif lane_count >= 4:
            reason = f"{lane} has the strongest vehicle flow, so the agent is extending green time there."
        elif lane_starvation >= 2:
            reason = f"{lane} has been delayed for multiple cycles, so the agent is rebalancing traffic."
        else:
            reason = f"{lane} is currently the best lane to serve based on overall traffic conditions."

        self.last_decision = {
            "lane": best_action["lane"],
            "duration": best_action["duration"],
            "score": self.normalize_score(scored_actions, best_score),
            "raw_score": round(best_score, 2),
            "reason": reason,
            "pressure": state["pressure"].copy(),
            "dominant_lane": state["dominant_lane"],
        }
        return self.last_decision

    def learn(self, chosen_lane, waits):
        for lane in LANES:
            if lane == chosen_lane:
                self.starvation[lane] = 0
            elif waits[lane] > 0:
                self.starvation[lane] += 1
            else:
                self.starvation[lane] = 0

        self.history.append(
            {
                "lane": chosen_lane,
                "wait_snapshot": waits.copy(),
            }
        )

    def get_telemetry(self):
        recent_steps = list(self.history)[-5:]
        average_wait = 0
        total_cars = 0
        if self.observation_history:
            average_wait = round(
                sum(item["avg_wait"] for item in self.observation_history)
                / len(self.observation_history),
                2,
            )
            total_cars = self.observation_history[-1]["total_cars"]

        fairness = max(self.starvation.values()) if self.starvation else 0

        return {
            "score": self.last_decision["score"],
            "raw_score": self.last_decision["raw_score"],
            "reason": self.last_decision["reason"],
            "starvation": self.starvation.copy(),
            "pressure": self.last_decision["pressure"].copy(),
            "dominant_lane": self.last_decision["dominant_lane"],
            "avg_wait": average_wait,
            "total_cars": total_cars,
            "fairness_risk": fairness,
            "recent_decisions": recent_steps,
        }


class TrafficEnvironment:
    def __init__(self):
        self.agent = TrafficAgent()
        self.reset()

    def reset(self):
        self.step = 1
        self.phase = "GREEN"
        self.active_lane = "North"
        self.remaining_time = 10
        self.counts = {lane: 0 for lane in LANES}
        self.waits = {lane: 0 for lane in LANES}
        self.agent.reset()

    def next_step(self, counts, waits):
        self.step += 1
        self.counts = counts
        self.waits = waits

        state = self.agent.observe(
            counts=self.counts,
            waits=self.waits,
            active_lane=self.active_lane,
            step=self.step,
        )
        decision = self.agent.choose_action(state)

        self.active_lane = decision["lane"]
        self.phase = "GREEN"
        self.remaining_time = decision["duration"]
        self.agent.learn(self.active_lane, self.waits)

    def get_data(self):
        return {
            "step": self.step,
            "active_lane": self.active_lane,
            "active_directions": self.active_lane,
            "phase": self.phase,
            "remaining_time": self.remaining_time,
            "agent": self.agent.get_telemetry(),
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

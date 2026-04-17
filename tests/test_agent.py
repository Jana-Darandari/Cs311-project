import pytest
from app import TrafficAgent, LANES


def test_generate_actions_returns_all_lanes():
    agent = TrafficAgent()
    # fake state with simple counts and waits
    state = {
        'counts': {lane: 2 for lane in LANES},
        'waits': {lane: 1 for lane in LANES},
        'starvation': {lane: 0 for lane in LANES},
        'active_lane': 'North',
        'total_cars': 8,
        'pressure': {lane: 0 for lane in LANES},
        'step': 1,
    }
    actions = agent.generate_actions(state)
    assert isinstance(actions, list)
    assert {a['lane'] for a in actions} == set(LANES)


def test_score_action_prefers_waiting_lane():
    agent = TrafficAgent()
    state = {
        'counts': {lane: 0 for lane in LANES},
        'waits': {lane: 0 for lane in LANES},
        'starvation': {lane: 0 for lane in LANES},
        'pressure': {lane: 0 for lane in LANES},
        'active_lane': 'North',
        'total_cars': 0,
        'step': 1,
    }
    # make East have high wait
    state['waits']['East'] = 10
    action_east = {'lane': 'East', 'duration': 10}
    action_north = {'lane': 'North', 'duration': 10}
    score_e = agent.score_action(state, action_east)
    score_n = agent.score_action(state, action_north)
    assert score_e > score_n


def test_choose_action_updates_last_decision():
    agent = TrafficAgent()
    counts = {lane: 1 for lane in LANES}
    waits = {lane: 0 for lane in LANES}
    state = agent.observe(counts, waits, active_lane='South', step=1)
    decision = agent.choose_action(state)
    assert 'lane' in decision and 'duration' in decision
    assert agent.last_decision['lane'] == decision['lane']

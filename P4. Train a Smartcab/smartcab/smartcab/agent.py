import random
import numpy as np
from environment import Agent, Environment
from planner import RoutePlanner
from simulator import Simulator
from collections import namedtuple
import pandas as pd
import os.path

stateRecord = namedtuple('stateRecord', ['light','opposing','nextWaypoint'])
validActions = [None, 'forward', 'left', 'right']

def argMax(Q, s):
        retA = None
        retV = 0
        if s in Q:
            for a in Q[s]:
                if Q[s][a] > retV:
                    retV = Q[s][a]
                    retA = a
        return(retA, retV)                    
        
class LearningAgent(Agent):
    """An agent that learns to drive in the smartcab world."""

    def __init__(self, env):
        super(LearningAgent, self).__init__(env)  # sets self.env = env, state = None, next_waypoint = None, and a default color
        self.color = 'red'  # override color
        self.planner = RoutePlanner(self.env, self)  # simple route planner to get next_waypoint
        # TODO: Initialize any additional variables here
        self.Q = {}
        self.alpha = 0.3
        self.gamma = 0.3
        self.explore = 0.99
        self.stateHist = {}
        self.run = 1        # Iteration counter for each alpha/gamma change
        self.trip = 0       # Trip counter in each iteration
        self.counter = 0    # Step counter in each run
        self.glNum = 0      # global counter
        self.rewards = 0 
        self.experiment = 'None'
        
    def reset(self, destination=None):
        self.planner.route_to(destination)
        # TODO: Prepare for a new trip; reset any variables here, if required
        self.trip += 1      # Increment the trip
        self.counter = 0    # Reset the counter for the next run
        #print('Trip:', self.trip)
            
        if self.trip == 100:
            hasHist = False            
            if os.path.isfile('runHist.pkl'):
                temp = pd.read_pickle('runHist.pkl')
                hasHist = True

            df = pd.DataFrame(self.stateHist).T
            df.columns = ['experiment','batch','trip','counter', 'light','opposing','oncoming','left','right','next_waypoint',
                          'action', 'qA', 'qV', 'reward', 'alpha', 'gamma', 'deadline','Explored']
            if hasHist:
                df = pd.concat([df, temp])
            df.to_pickle('runHist.pkl')
            self.stateHist = {}
        
    def update(self, t):
        # Gather inputs
        self.next_waypoint = self.planner.next_waypoint()  # from route planner, also displayed by simulator
        inputs = self.env.sense(self)
        deadline = self.env.get_deadline(self)
        # Possibly TODO: Add a 'isGoalToRight' metric to the state so the car can 
        # learn right on red when the goal is also to the right.        
        
        # TODO: Update state
        opposing = False
        if inputs[self.next_waypoint.replace('forward','oncoming')]:
            opposing = True
        self.state = stateRecord(inputs['light'], opposing, self.next_waypoint)
        
        # Initialize the new state if it's novel
        if self.state not in self.Q:
            self.Q[self.state] = {'left':0, 'right':0, 'forward':0, None:0}
        self.counter += 1
        
        
        # TODO: Select action according to your policy  
        qA, qV = argMax(self.Q, self.state)
        choseExpl = False
        if random.randrange(0, 100)/100.0 < self.explore or qV == 0:
            action = validActions[random.randint(0,3)]
            if self.explore > 0.00:
                self.explore = self.explore - 0.01
            choseExpl = True
        else:
            action = qA
            
        # Execute action and get reward
        reward = self.env.act(self, action)
        rInputs = self.env.sense(self)
        # TODO: Learn policy based on state, action, reward
        nOpposing = False
        if rInputs[self.next_waypoint.replace('forward','oncoming')]:
            nOpposing = True
            
        s = stateRecord(rInputs['light'], nOpposing, self.next_waypoint)
        
        self.Q[self.state][action] = self.Q[self.state][action] * (1- self.alpha) + self.alpha * (reward + self.gamma * argMax(self.Q, s)[1])
        
        writeout = 'Lights:{} Goal:{} '.format( str(self.state[0]), str(self.state[2])) 
        writeout += 'Action:{} Reward:{} Qest:{} Expl:{} Exp:{}'.format(str(action), str(reward), str(self.gamma * argMax(self.Q, s)[1]), choseExpl, self.explore)
        
        #print(writeout)
        self.rewards += reward
        n = str(self.glNum) +'.' + str(self.trip) + '.' + str(self.counter)
        self.stateHist[n] = [self.experiment, self.glNum ,self.trip, self.counter,  
                            inputs['light'], opposing, inputs['oncoming'], inputs['left'], 
                            inputs['right'], self.next_waypoint, 
                            action, qA, qV, reward, self.alpha, self.gamma, deadline, choseExpl]

        #print "LearningAgent.update(): deadline = {}, inputs = {}, action = {}, reward = {}, step = {}".format(deadline, inputs, action, reward, self.counter)  # [debug]


def run():
    """Run the agent for a finite number of trials."""
    optimize = True
    globalNum = 0
    if optimize:
        for alpha in range(1, 11):
            for n in range(1, 11):
                e = Environment()  # create environment (also adds some dummy traffic)
                a = e.create_agent(LearningAgent)  # create agent
                a.experiment  ='alpha'
                e.set_primary_agent(a, enforce_deadline=True)  # set agent to track
                sim = Simulator(e, update_delay=0)  # reduce update_delay to speed up simulation
                a.glNum = globalNum
                globalNum += 1
                a.alpha = (alpha / 20.0) + 0.2
                a.run += 1
                a.counter = 0
                a.trip = 0
                sim.run(n_trials=100) 
            
        for gamma in range(1, 11):
            for n in range(1, 11):
                e = Environment()  # create environment (also adds some dummy traffic)
                a = e.create_agent(LearningAgent)  # create agent
                a.experiment  ='gamma'
                e.set_primary_agent(a, enforce_deadline=True)  # set agent to track
                sim = Simulator(e, update_delay=0)  # reduce update_delay to speed up simulation
                a.glNum = globalNum
                globalNum += 1
                a.gamma = (gamma / 20.0) + 0.2
                a.run += 1
                a.counter = 0
                a.trip = 0
                sim.run(n_trials=100)

if __name__ == '__main__':
    run()

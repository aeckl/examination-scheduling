import sys
import os
PATHS = os.getcwd().split('/')
PROJECT_PATH = ''
for p in PATHS:
    PROJECT_PATH += '%s/' % p
    if p == 'examination-scheduling':
        break
sys.path.append(PROJECT_PATH)

import numpy as np
import random as rd
from collections import defaultdict
from copy import deepcopy

from model.instance import build_random_data
from heuristics.tools import get_coloring, swap_color_dictionary, to_binary
from heuristics.schedule_rooms import schedule_greedy

import model.constraints_handler as constraints

from gurobipy import Model, quicksum, GRB, GurobiError

#
# Responsible team member: ROLAND
#
# TODO: Currently works only if n > p!!! Change
# TODO: n = 4, p = 6, seed = 37800
# 

def get_changing_colors(color_schedule, color1, color2):
    
    changed = set()
    changed.add(color1)
    if color2 is not None:
        changed.add(color2)
    return changed

    
def obj3(color_schedule, exam_colors, color_conflicts):
    
    # sum min distance to neighboring color nodes
    #for exam in exam_colors:
        #print exam
        #print color_conflicts[exam]
    distance_sum = 0.0
    d_n = [ 0 ] * len(exam_colors)
    for exam in exam_colors:
        if len(color_conflicts[exam]) > 0:
            distance_sum += min( [abs(color_schedule[exam_colors[exam]] - color_schedule[d]) for d in color_conflicts[exam]] ) 
            d_n[exam] = min( [abs(color_schedule[exam_colors[exam]] - color_schedule[d]) for d in color_conflicts[exam]] ) 
    
    return 1.0*distance_sum/len(exam_colors)


def obj3_optimized(color_schedule, exam_colors, color_conflicts):
    
    # sum min distance to neighboring color nodes
    distance_sum = 0.0
    for exam in exam_colors:
        if len(color_conflicts[exam]) > 0:
            hi = color_schedule[exam_colors[exam]]
            distance_sum += min( [abs(hi - color_schedule[d]) for d in color_conflicts[exam]] ) 
    
    return 1.0*distance_sum/len(exam_colors)


def obj4(color_schedule, exam_colors, color_exams, color_conflicts, c_n = None, d_n = None, change_colors = None):
    '''
        sum min distance only consider changed colors!
    '''
    if d_n is None or change_colors is None:
        return obj3(color_schedule, exam_colors, color_conflicts)
    
    exams = set()    
        
    for exam in exam_colors:
        # exam changes
        if exam_colors[exam] in change_colors:
         #   print exam
            exams.add(exam)
            continue
        # conflicting exam changes
        for color in color_exams:
            if color in color_conflicts[exam]:
          #      print "---> ", exam
                exams.add(exam)
                break
            
    print len(exams), len(exam_colors)
    
    for exam in exams:
        if len(color_conflicts[exam]) > 0:
            mindex = np.argmin([abs(color_schedule[exam_colors[exam]] - color_schedule[d]) for d in color_conflicts[exam]])
            color = color_conflicts[exam][mindex]
            
            d_n[exam] = abs(color_schedule[exam_colors[exam]] - color_schedule[color])
            assert d_n[exam] == min( [abs(color_schedule[exam_colors[exam]] - color_schedule[d]) for d in color_conflicts[exam]] )
            d_n[exam] = min( [abs(color_schedule[exam_colors[exam]] - color_schedule[d]) for d in color_conflicts[exam]] )
       
        
    return np.mean(d_n)


def obj5(color_schedule, exam_colors, conflicts, K = None):
    
    times = [ color_schedule[exam_colors[exam]] for exam in exam_colors ]
    
    distance_sum = 0.0
    n_students = 0.0
    for i in exam_colors:
        if len(conflicts[i]) > 0:
            d_i = [abs(times[i] - times[j]) for j in conflicts[i]]
            js = [ j for j, d in enumerate(d_i) if d == min(d_i) ]
            for j in js:
                distance_sum += d_i[j] * K[i, j]
                n_students += K[i,j]
            
    return distance_sum/n_students


def obj_time(color_schedule, exam_colors, color_conflicts, K = None, conflicts = None):

    if K is not None and conflicts is not None:
        return obj5(color_schedule, exam_colors, conflicts, K)
        
    return obj3_optimized(color_schedule, exam_colors, color_conflicts)


def is_feasible(color_schedule, statespace):
    '''
        For a given color_schedule check if it is feasible in the given statespace
    '''
    for color in statespace:
        if color_schedule[color] not in statespace[color]:
            return False
    return True
    
    
def get_infeasible(color_schedule, statespace):
    infeasible = []
    for color in statespace:
        if color_schedule[color] not in statespace[color]:
            infeasible.append(color)
    return infeasible
 
 
def propose_color(color, color_schedule, statespace):
    
    '''
    For a given color make a proposal. Swap if necessary!
    '''
    
    old_slot = color_schedule[color]
    
    # draw new time slot
    new_slot = rd.choice(statespace[color])
    while new_slot == old_slot:
        #print "="#, #statespace[color]
        new_slot = rd.choice(statespace[color])
        
    # determine if we need to swap colors
    color2 = None
    if new_slot in color_schedule:
        color2 = color_schedule.index(new_slot)
    
    return color, new_slot, color2, old_slot


def make_proposal(color_schedule, statespace, n_colors, log=False):
    '''
        Make a proposal for the simulated annealing.
        This loops until a feasible solution is found.
        Feasibility is determined using the statespace.
    '''

    feasible = False
    count_feas = 0
    
    # loop until feasible
    while not feasible:
        
        # draw color to change
        color = rd.randint(0, n_colors-1)
        if len(statespace[color]) == 1:
            print "no use"
            continue
        elif len(statespace[color]) == 0:
            print "impossible!"
            
        color, new_slot, color2, old_slot = propose_color(color, color_schedule, statespace)
        
        feasible = True
        
        count_feas += 1
        
    if log and count_feas > 1: print "while", count_feas
    
    return color, new_slot, color2, old_slot


def swap(color_schedule, color, new_slot, color2, old_slot):
    color_schedule[color] = new_slot
    if color2 is not None:
        color_schedule[color2] = old_slot
        

def get_color_conflicts(color_exams, exam_colors, conflicts):
    '''
        For each exam, get a list of colors with conflicting exams in them
    '''
    # TODO: TEST!

    color_conflicts = defaultdict(list)
    for i in exam_colors:
        color_conflicts[i] = sorted(set( exam_colors[j] for j in conflicts[i] ))
    return color_conflicts        
        

def find_feasible_start(n_colors, h, statespace, conflicts, verbose=False):
    
    model = Model("TimeFeasibility")
    p = len(h)
    y = {}
    # y[i,k] = if color i gets slot l
    for i in range(n_colors):
        for l in range(p):
            y[i,l] = model.addVar(vtype=GRB.BINARY, name="y_%s_%s" % (i,l))

    model.update()

    # Building constraints...    
    
    # c1: all get one
    for i in range(n_colors):
        model.addConstr( quicksum([ y[i, l] for l in range(p) ]) == 1, "c1")

    # c2: each slot needs to be used tops once
    for l in range(p):
        model.addConstr( quicksum([ y[i, l] for i in range(n_colors) ]) <= 1, "c2")    

    ### c3: statespace constraints
    for i in range(n_colors):
        #print l, h[l], i, [s for s in statespace]
        model.addConstr( quicksum([ y[i, l] for l in range(p) if h[l] not in statespace[i] ]) == 0, "c3")    
    
    # objective: minimize conflicts
    #obj = quicksum([ y[i,l] * y[j,l] for l in range(p) for i in range(n_colors) for j in range(i+1, n_colors) ]) 
    obj = quicksum([ sum(y[i,l] for i in range(n_colors)) for l in range(p)  ]) 
    #obj = 0
    model.setObjective(obj, GRB.MINIMIZE)
    
    if not verbose:
        model.params.OutputFlag = 0
    
    model.optimize()

    # return best room schedule
    color_schedule = []
    if model.status == GRB.INFEASIBLE:
        return color_schedule
                    
    for i in range(n_colors):
        for l in range(p):
            v = model.getVarByName("y_%s_%s" % (i,l)) 
            if v.x == 1:
                color_schedule.append(h[l])
                break
            
    return color_schedule

    #except GurobiError:
        #return None



def simulated_annealing(exam_colors, data, beta_0 = 0.3, max_iter = 1e4, lazy_threshold = 1.0, acceptance_threshold=0.0, statespace = None, color_schedule = None, color_exams = None, log = False, log_hist=False, debug = False):
    '''
        Simulated annealing
        @Param exam_colors: coloring of conflict graph
        @Param data: data dictionary 
        @Param statespace: dictionary with list of possible states for each color
        @Param beta_0: Start of cooling schedule
        @Param max_iter: Number of annealing iterations to perform
        @Param lazy_threshold: Check if the best solution so far has changed much. If set to 1, no lazy evaluation is performed.
        @Param acceptance_threshold: Break if acceptance rate is below this value
        @Param statespace: For each color, which slots are eligible?
        @Param color_schedule: Starting solution (if infeasible, random generation)
        @Param color_exams: A dict with a list of exams for each color
        @Param log: General logging messages
        @Param log_hist: Record all values for performance plotting
        @PAram debug: Do asserts or not?
        
        Pseudocode:
        1. choose random color and eligible time slot
        2. find color if the slot is already taken. If so, swap them
        3. calculate objective
        4. accept proposal? If not, revert swap
    '''
    
    h = data['h']
    conflicts = data['conflicts']
    n_exams = len(exam_colors)
    n_colors = len(set(exam_colors.values()))
    
    if debug:
        assert list(exam_colors) == sorted(exam_colors), "Error: Dictionary keys need to be sorted!!"
        assert type(exam_colors) == dict, "ERROR: coloring needs to be a dictionary!"
        assert type(data) == dict, "ERROR: data needs to be a dictionary!"
        assert color_schedule is None or type(color_schedule) == list, "ERROR: color_schedule needs to be either None or a list!"
        assert n_colors <= len(h), "Currently only tables with less colors than timeslots are plannable" 
        if statespace is not None:
            for color in color_exams:
                assert len(statespace[color]) > 1, "Error: statespace needs to contain more than one state for each colors!"
                for slot in statespace[color]:
                    assert schedule_greedy(color_exams[color], h.index(slot), data, verbose = False) is not None
        for exam in exam_colors:
            assert (exam_colors[exam] >= 0) and (exam_colors[exam] <= n_colors), "Error: Colors need to be in range 0, n_colors"
                
                
    # for each color get list of exams
    if color_exams is None:
        color_exams = swap_color_dictionary(exam_colors)
    
    assert len(color_exams) <= len(h)
    
    # get conflicts of colors
    color_conflicts = get_color_conflicts(color_exams, exam_colors, conflicts)
    
    #assert min([len(statespace[i]) for i in statespace]) > 1, min([len(statespace[i]) for i in statespace])
    
    # the state space for each coloring, calculated from the 
    if statespace is None:
        statespace = { color: h for color in color_exams }
    
    # initialize the time slots randomly
    if color_schedule is None:
        if log: print "SEARCHING START"
        color_schedule = find_feasible_start(n_colors, h, statespace, conflicts, verbose=False)
        
        if len(color_schedule) < n_colors:
            return None, 0
        #else:
            #print "Found one!"
    
    assert len(color_schedule) == len(set(color_schedule)), len(color_schedule) - len(set(color_schedule))
    if len(color_schedule) != len(set(color_schedule)): print len(color_schedule) - len(set(color_schedule))
    
    if log: 
        y_binary = to_binary(exam_colors, color_schedule, h)
        print constraints.time_feasible(y_binary, data).values()
    
    
    # best values found so far
    best_color_schedule = deepcopy(color_schedule)
    best_value = obj_time(color_schedule, exam_colors, color_conflicts, K=data['K'], conflicts = conflicts)
    
    # initialization and parameters simulated annealing
    beta = beta_0
    #schedule = lambda t: beta_0 * np.log(1+np.log(1+t))
    schedule = lambda t: beta_0 * np.log(1+t)
    
    # initialize loop
    iteration = 0
    value = best_value
    old_value = best_value
    if log_hist:
        history = []
        best_history = []
        acceptance_rates = []
    accepted = 0
    best_value_duration = 0
    
    
    while iteration < max_iter:
        
        iteration += 1
        beta = schedule(iteration)
        
        if log:
            print("Iteration: %d" %iteration)
            print color_schedule
        
        '''
            make proposal
        '''

        # get colors to change and their slot values
        if log: print "MAKE PROPOSAL"
        color, new_slot, color2, old_slot = make_proposal(color_schedule, statespace, n_colors, log=False)
        if log: print "OK"
        #if log: 
        if log: print color, new_slot, color2, old_slot
        #changed = get_changing_colors(color_schedule, color, color2)
        
        # perform changes to color_schedule
        swap(color_schedule, color, new_slot, color2, old_slot)
        
        #print color_schedule
        y_binary = to_binary(exam_colors, color_schedule, h)
        if log: print "new slot", constraints.time_feasible(y_binary, data).values()
    
        if log: print color, color2, color_schedule
            
        if debug: assert len(set(color_schedule)) == len(color_schedule), "time table needs to be uniquely determined!" 
        
        '''
            get objective value
        '''
        
        value = obj_time(color_schedule, exam_colors, color_conflicts, K=data['K'], conflicts = conflicts)
    
        '''
            acceptance step.
            exp(+ beta) because of maximization!
        '''
        if log:
            print "Obj: %0.2f" % value
            print np.exp(-beta * (value - old_value))
        #print value, old_value, np.exp( beta * (value - old_value))
        
        if value > old_value or rd.uniform(0,1) <= np.exp( beta * (value - old_value) ):
            
            if log: print "Accepted"
            
            accepted += 1
            old_value = value
            #d_n = d_n_tmp
            # save value if better than best
        
            # build binary variable 
            if debug: print "TOBINARY"
            if log:
                y_binary = to_binary(exam_colors, color_schedule, h)
                print constraints.time_feasible(y_binary, data)
    
        
            if value > best_value:
                best_value = value
                best_color_schedule = deepcopy(color_schedule)
                best_value_duration = 0
    
                if log:
                    print("better!")
                
        else:
            # reject: revert state change, swap back
            color_schedule[color] = old_slot
            if color2 is not None:
                color_schedule[color2] = new_slot
                
        best_value_duration += 1
        if log_hist:
            history.append(value)
            best_history.append(best_value)
            acceptance_rates.append(accepted/float(iteration))
        
        if log: print best_value_duration/float(max_iter)
        # TODO: best value is attained 50% of the time, stop optimizing
        if log_hist and lazy_threshold < 1.0 and best_value_duration/float(max_iter) > lazy_threshold:
            if log: print "Wuhu!", iteration
            break
        if acceptance_threshold > 0.0 and accepted/float(iteration) <= acceptance_threshold:
            if log: print "Wuhu!", iteration
            break
        

    if log_hist:
        print "End beta:", beta
        print "iterations:", iteration
        print "acceptance rate:", accepted/float(iteration)
        #print "Opt hist:", best_history
        
        import matplotlib.pyplot as plt
        import inputData.tools as csvtools
        
        csvtools.write_csv("%sheuristics/plots/annealing_history_%d_%d.csv"%(PROJECT_PATH, max_iter, beta_0), {"x":range(len(history)), "y":history})
        csvtools.write_csv("%sheuristics/plots/annealing_best_%d_%d.csv"%(PROJECT_PATH, max_iter, beta_0), {"x":range(len(history)), "y":best_history})
        csvtools.write_csv("%sheuristics/plots/annealing_accept_%d_%d.csv"%(PROJECT_PATH, max_iter, beta_0), {"x":range(len(history)), "y":acceptance_rates})
        
        plt.clf()
        plt.plot(history)
        plt.ylabel('obj values')
        plt.savefig("%sheuristics/plots/annealing.png"%PROJECT_PATH)
        
        plt.clf()
        plt.plot(best_history)
        plt.ylabel('best history')
        plt.savefig("%sheuristics/plots/annealing_best.png"%PROJECT_PATH)
        
        plt.clf()
        plt.plot(acceptance_rates)
        plt.ylabel('best history')
        plt.savefig("%sheuristics/plots/annealing_rate_accept.png"%PROJECT_PATH)
        #print "annealing history plot in plots/annealing.png"
    return best_color_schedule, best_value
    

def schedule_times(coloring, data, beta_0 = 10, max_iter = 1000, n_chains = 1, n_restarts = 1, statespace = None, color_exams = None, debug = False):
    '''
        Schedule times using simulated annealing
        TODO: Description
    '''
    #debug = True
    log_hist = False
    #log_hist = True
    if debug:
        log_hist = True
    color_schedules = []
    values = []
    for chain in range(n_chains):
        color_schedule = None
        for restart in range(n_restarts):
            color_schedule, value = simulated_annealing(coloring, data, beta_0 = beta_0, max_iter = max_iter, statespace = statespace, color_exams=color_exams, color_schedule = color_schedule, log_hist = log_hist)
        if color_schedule is not None:
            color_schedules.append(deepcopy(color_schedule))
            values.append(value)
    
    if debug:
        print "Exiting due to debugging schedule_times"
        exit(0)
    
    if len(values) == 0:
        return None, 0
    
    best_index, best_value = max( enumerate(values), key = lambda x : x[1] )
            
    return color_schedules[best_index], best_value
    

if __name__ == '__main__':
    
    n = 150
    r = 60
    p = 60
    
    prob_conflicts = 0.15
    
    rd.seed(4200)
    data = build_random_data( n=n, r=r, p=p, prob_conflicts=prob_conflicts, build_Q = False)
    
    conflicts = data['conflicts']
    coloring = get_coloring(conflicts)
    
    from time import time
    from model.instance import build_smart_random
    from heuristics.johnson import Johnson
    n_colorings = 10
    
    js = Johnson(data, n_colorings = n_colorings, n_colors = p)
    colorings = js.generate_colorings()
    #print colorings
    for i in range(n_colorings):
        
        coloring = colorings[i]
        
        n_colors = len(set(coloring.values()))
        if n_colors == p:
            break
    
    n_colors = len(set(coloring.values()))
    print "Colors:", n_colors
        
    # annealing params
    max_iter = 6000
    beta_0 = 100
    print "Start beta: %f" %beta_0
    print "Iterations: %d" %max_iter
    
    rd.seed(420)
    
    # run annealing
    from time import time
    n_runs = 1
    t1 = time()
    for i in range(n_runs):
        times, v1 = simulated_annealing(coloring, data, beta_0 = beta_0, max_iter = max_iter, log_hist=(i == 0), log=False)
    #times, v2 = simulated_annealing(coloring, data, beta_0 = beta_0, max_iter = max_iter, color_schedule= times, log_hist=log_hist)
    t1 = (time() - t1)*1.0/n_runs
    rt1 = t1/max_iter
    print "Time: %0.3f" %t1, "Value:", v1
    
    
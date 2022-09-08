#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import collections
from time import time

from model.instance import force_data_format, build_random_data
import GurobiModel.GurobiLinear_v_8_removed_obj as gurobi
from gurobipy import GurobiError

from heuristics.AC import AC
from heuristics.schedule_times import schedule_times
from heuristics.schedule_rooms import schedule_rooms
import heuristics.tools as tools
import model.constraints_handler as constraints
from heuristics.schedule_rooms import schedule_rooms_in_period, schedule_greedy, schedule_rooms_in_period



def build_statespace_similar_periods(coloring, data):
    
    #print "Similar periods"
    
    h = data['h']
    
    # refactor dicts
    color_exams = tools.swap_color_dictionary(coloring)
    
    statespace = { color: [] for color in color_exams }
    
    # get similar periods
    similar_periods = data['similar_periods']
    
    for color in color_exams:
        
        periods = range(data['p'])
        while len(periods) > 0:
            
            period = periods[0]
            greedy_schedule = schedule_greedy(color_exams[color], period, data)
            
            feasible = greedy_schedule is not None
            
            if feasible:
                statespace[color].append(h[period])
                    
            for period2 in similar_periods[period]:
                if period2 not in periods:
                    continue
                if period2 != period and feasible:
                    statespace[color].append(h[period2])
                periods.remove(period2)
            periods.pop(0)
        
        if len(statespace[color]) == 0:
            return None, None

    return statespace, color_exams


def build_statespace_exam_slots(coloring, data):
    
    h = data['h']
    exam_slots = data['exam_slots']
    
    # refactor dicts
    color_exams = tools.swap_color_dictionary(coloring)
    
    color_slots = collections.defaultdict(set)
    for color in color_exams:
        for exam in color_exams[color]:
            #color_slots[color].update(exam_slots[exam])
            color_slots[color].update([ slot for slot in exam_slots[exam] if len(color_slots[color]) == 0 or slot in color_slots[color] ])
        
    #print color_exams
    #print sorted(coloring.values())
    
    # empty statespace -> init
    statespace = { color: [] for color in color_exams }
    for color in color_exams:
        
        for time in color_slots[color]:
            period = h.index(time)
            
            greedy_schedule = schedule_greedy(color_exams[color], period, data)
            if greedy_schedule is not None:
                statespace[color].append(time)
                #print color, period, "appended"
            #else:
                #ILP_schedule = schedule_rooms_in_period(color_exams[color], period, data)
                #if ILP_schedule is not None:
                    #statespace[color].append(time)
                    #print color, period, "appended, ILP"
                #else:
                    #print "denied, ILP"
                
        if len(statespace[color]) == 0:
            return None, None

    return statespace, color_exams



def build_statespace(coloring, data):
    '''
        Build statespace by checking feasibility for every color and every possible time slot.
        If the similar_periods field is present in the data, this is spead up by considering duplicate times slots.
    '''
    
    if 'exam_slots' in data and len(data['exam_slots']) > 0:
        return build_statespace_exam_slots(coloring, data)
    
    if 'similar_periods' in data:
        return build_statespace_similar_periods(coloring, data)
    
    h = data['h']
    
    # refactor dicts
    color_exams = tools.swap_color_dictionary(coloring)
    
    # empty statespace -> init
    statespace = { color: [] for color in color_exams }
    
    for color in color_exams:
        for period, time in enumerate(h):
            greedy_schedule = schedule_greedy(color_exams[color], period, data)
            if greedy_schedule is not None:
                statespace[color].append(time)
        if len(statespace[color]) == 0:
            return None, None

    return statespace, color_exams



def heuristic(coloring, data, gamma = 1, max_iter = 100, beta_0 = 10, debug=False):
    '''
        The heuristiv which iteratively solves first the time scheduling problem, and afterwards the room scheduling problems.
        @Param: coloring dictionary which gives the color for each exam i
        @Param: data is the data and setup of the problem
        @Param: gamma is the weighting of room and time objectives
        @Returnvalues:
        room_schedule: binary. 1 if exami i in room k
        color_schedule: dict of ints
        obj_val: combined objective
    '''
    #print coloring
    #colors = coloring.values()
    #print len(set(colors)), len(data['h']), data['p']
    #color_schedule = dict()
    #for slot, color in enumerate(set(colors)):
        #color_schedule[color] = data['h'][slot]
    #y_binary = tools.to_binary(coloring, color_schedule, data['h'])
    #print constraints.time_feasible(y_binary, data)
    
    # check feasibility
    if debug: print "Building Statespace"
    statespace, color_exams = build_statespace(coloring, data)
    #print "Statespace", [len(statespace[i]) for i in statespace], min([len(statespace[i]) for i in statespace])
    if statespace is None or min([len(statespace[i]) for i in statespace]) <= 1:
        if debug: print "infeasible statespace"
        return None, None, None, sys.maxint
    
    #for i in statespace:
        #print i, len(statespace[i]
    #exit(0)
    
    for i in statespace:
        assert len(statespace[i]) == len(set(statespace[i]))
    
    # create time schedule permuting the time solts for each coloring
    if debug: print "ANNEALING"
    color_schedule, time_value = schedule_times(coloring, data, max_iter = max_iter, beta_0 = beta_0, statespace = statespace, color_exams = color_exams)
    
    if color_schedule is None:
        if debug: print "no feasible starting point"
        return None, None, None, sys.maxint
    
    # build binary variable 
    if debug: print "TOBINARY"
    y_binary = tools.to_binary(coloring, color_schedule, data['h'])
    
    if y_binary is None or not all(constraints.time_feasible(y_binary, data)):
        if debug: print constraints.time_feasible(y_binary, data)
        return None, None, None, sys.maxint
    
    # create room schedule
    if debug: print "SCHDULE ROOMS"
    room_schedule, room_value = schedule_rooms(coloring, color_schedule, data, greedy = True)
    
    if debug: print "DONE"
    
    # if infeasible, return large obj_val since we are minimizing
    if room_schedule is None:
        if debug: print constraints.room_feasible(room_schedule, data)
        return None, None, None, sys.maxint

    # evaluate combined objectives
    obj_val = room_value - gamma * time_value
        
    return room_schedule, y_binary, color_schedule, obj_val


import multiprocessing

def execute_heuristic(chunk): 
    x, y, s, v = heuristic(chunk["coloring"], chunk["data"], gamma = chunk["gamma"], max_iter = chunk["max_iter"], beta_0 = chunk["beta_0"], debug=chunk["debug"])       
    return {"index": chunk["index"], "x":x, "y":y, "s":s, "v":v}

        
def optimize(meta_heuristic, data, epochs=10, gamma = 1, annealing_iterations = 1000, annealing_beta_0 = 10, lazy_threshold = 1.0, verbose = False, log_history = False, debug=False, parallel=False):
    
    # init best values
    x, y, obj_val = None, None, sys.maxint
        
    if log_history:
        logger = collections.defaultdict(collections.defaultdict)
    
    best_value_duration = 0
    
    # iterate
    for epoch in range(epochs):
        
        if verbose:
            print epoch
        xs, ys, obj_vals = dict(), dict(), dict()
        color_schedules = dict()

        # Generate colourings
        if debug: print "Building Colorings"
        colorings = meta_heuristic.generate_colorings()
        
        for coloring in colorings:
            
            assert len(set(coloring.values())) == max(coloring.values())+1, sorted(set(coloring.values()))
            
        
        if len(colorings) == 0:
            print "Infeasible colorings"
            break
            
        
        # calculate results
        cores = 1
        if parallel == True:
            cores = multiprocessing.cpu_count()
            print "Using", cores, "processes"
            pool = multiprocessing.Pool(cores)
            
            # pack colorings in pickable format
            data_chunks = []
            for index, coloring in enumerate(colorings):
                data_chunks.append({"coloring": coloring, "index": index, "data": data, "gamma":gamma, "max_iter": annealing_iterations, "beta_0": annealing_beta_0, "debug": debug})
                
            results = pool.map_async(execute_heuristic, data_chunks)
            results = results.get()
            
            pool.close()
            pool.join()
            
        else:
            results = map(lambda x: heuristic(x, data, gamma = gamma, max_iter = annealing_iterations, beta_0 = annealing_beta_0, debug=debug), colorings)
            
        ## evaluate all results
        for ind, result in enumerate(results):
            # evaluate heuristic
            if parallel:
                xs[ind], ys[ind], color_schedules[ind], obj_vals[ind] = result["x"], result["y"], result["s"], result["v"]
            else:
                xs[ind], ys[ind], color_schedules[ind], obj_vals[ind] = result[0], result[1], result[2], result[3]
        # filter infeasibles
        values = filter(lambda x: x[1] < sys.maxint, enumerate(obj_vals.values()))
        
        # check feasibility
        if len(values) == 0:
            #print "infeasible"
            if log_history:
                tools.log_epoch(logger, epoch, obj_val = obj_val, n_feasible = 0.0) 
            continue
        
        # search for best coloring
        best_index, best_value = min( values, key = lambda x: x[1] )

        if log_history:
            worst_index, worst_value = max( values, key = lambda x: x[1] )
            tools.log_epoch(logger, epoch, obj_val = obj_val, best_value=best_value, n_feasible = 1.0 * len(values) / len(colorings))#, mean_value=np.mean(map(lambda x:x[1],values)), worst_value=worst_value, ) 
                      
        # Update meta heuristic
        meta_heuristic.update(obj_vals.values(), best_index = best_index, time_slots = color_schedules)

        best_value_duration += 1
        
        # save best value so far.. MINIMIZATION
        if best_value < obj_val:
            x, y, obj_val = xs[best_index], ys[best_index], best_value    
            
            best_value_duration = 0
        
    if log_history:
        return x, y, obj_val, logger
    else:
        return x, y, obj_val, None


      
        
if __name__ == '__main__':
    
    print "Nothing implemented here.\nRun 'tests/test_scheduler.py' instead!"
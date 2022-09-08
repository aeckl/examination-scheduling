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

from time import time
from inputData import examination_data
from heuristics.MetaHeuristic import RandomHeuristic, RandomHeuristicAdvanced
import heuristics.schedule_exams as scheduler
from heuristics.johnson import Johnson
from heuristics.AC import AC
import heuristics.tools as tools

if __name__ == '__main__':
    
    threshold = 0
    gamma = 10
    n_colorings = 50
    epochs = 50
    annealing_iterations = 100
    
    data = examination_data.read_data(semester = "16S", threshold = threshold)
    
    data['similar_periods'] = tools.get_similar_periods(data)
    
    print data['n'], data['r'], data['p']

    Heuristic = RandomHeuristicEqualized(data, n_colorings = n_colorings)
    Heuristic = Johnson(data, n_colorings = n_colorings, n_colors = data['p'])
    Heuristic = AC(data, num_ants = n_colorings, n_colors = data['p'])
    
    t = time()
    x, y, v, logger = scheduler.optimize(Heuristic, data, epochs = epochs, gamma = gamma, annealing_iterations = annealing_iterations, verbose = False, log_history = True)
    print "Time:", time()-t
    print "VALUE:", v
    
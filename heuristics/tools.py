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
import networkx as nx
from model.instance import build_random_data
from copy import deepcopy


def swap_color_dictionary(dic):
    '''
        swap dict
        @Input: Dictionary {exam: color, }
        @Output: Dictionary {color: [exam1, exam2,...], }
    '''
    out = defaultdict(set)
    for k, v in dic.items():
         out[v].add(k)

    for v in out:
        out[v]=list(out[v])     
    return dict(out)



def get_similar_periods(data):
    '''
        For each period return those periods which have the same room conditions
    '''
    p = data['p']
    T = data['T']
    room_footprint = defaultdict(list)
    rooms = defaultdict(list)
    for period in range(p):
        rooms[period] = [ T[k][period] for k in range(data['r']) ]
        room_footprint[''.join(map(str,rooms[period]))].append(period)
    
    similar_periods = defaultdict(list)
    for period in range(p):
        similar_periods[period] = [l for l in room_footprint[''.join(map(str,rooms[period]))] if l != period]
    #for key in similar_periods:
        #print key, similar_periods[key]
    
    return similar_periods
        
        

def get_coloring(conflicts):
    '''
        Generate greedy coloring
        @Input: Conflicts lists
        @Output: A feasible coloring
    '''
    graph = nx.Graph()
    for c in conflicts:
        graph.add_node(c)
        for d in conflicts[c]:
            graph.add_edge(c, d)
    return nx.coloring.greedy_color(graph)


def to_binary(coloring, color_schedule, h):
    '''
        Convert color schedule to binary y_i,l variable
    '''
    if color_schedule is None:
        return None
    
    hdict = dict()
    for i, hi in enumerate(h):
        hdict[hi] = i
        
    y = defaultdict(int)
    for i in coloring:
        l = hdict[color_schedule[coloring[i]]]
        y[i,l] = 1.0
    
    return y


def log_epoch(logger, epoch, **kwargs):
    ''' 
        Save epoch data in logger.
        Logger[key] is a dictionary!
    '''
    for key in kwargs:
        logger[key][epoch] = kwargs[key]
        


if __name__ == '__main__':
    n = 10
    p = 5
    n_colors = 3
    assert n_colors < p
    
    coloring = { i: i % n_colors for i in range(n) }
    print coloring
    h = [2*l for l in range(p)]
    color_schedule = [ h[l] for l in range(n_colors) ]
    
    y = to_binary(coloring, color_schedule, h)
    for i in range(n):
        for l in range(p):
            print (i,l), y[i,l]
            
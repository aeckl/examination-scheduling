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

# this script produce instances:
#   - we get it from files
#   - we produce it randomly
#   - or we find simple specific instance

import random as rd
import numpy as np
# from load_rooms import get_random_room_capacity
from collections import defaultdict

from model.data_format import force_data_format


from inputData.read import read_real_data


@force_data_format
def build_random_data(**kwards):
    """ @param n, r, p: number of exams, rooms, periods
    """
    n, r, p = kwards.get('n', 0), kwards.get('r', 0), kwards.get('p', 0)
    prob_conflicts = kwards.get('prob_conflicts', 0.5)
    build_Q = kwards.get('build_Q', True)

    data = {'n': n, 'r': r, 'p': p}
    # we generate a random number of student between 5 and 10 per exam
    data['s'] = [int(5 + 6 * rd.random()) for i in range(n)]
    # the room has a capacity between 5 and 20
    data['c'] = [int(5 + 16 * rd.random()) for k in range(r)]
    # hours between starting day and starting periods are fixed equal to 2
    data['h'] = [2 * l for l in range(p)]

    data['build_Q'] = build_Q

    # conflicts is a list containing a list of conflicts for each index i
    data['conflicts'] = defaultdict(list)
    for i in range(n):
        data['conflicts'][i] = [j for j in range(i + 1, n) if rd.random() <= prob_conflicts]

    # locking time is a list for each room k with locking times
    data['locking_times'] = defaultdict(list)
    for k in range(r):
        data['locking_times'][k] = [l for l in range(p) if rd.random() <= 0.1]

    return data


@force_data_format
def build_small_input():
    small_input = {
        'n': 5,  # 5 exams
        'r': 3,  # 3 rooms
        'p': 3,  # 3 periods
        's': [5, 3, 4, 2, 1],  # number of students per exams
        'c': [5, 4, 1],  # number os seats per rooms
        'Q': [[0, 0, 0, 1, 1],
              [0, 0, 0, 1, 0],
              [0, 0, 0, 1, 1],
              [1, 1, 1, 0, 1],
              [1, 0, 1, 1, 0]],  # Conflicts matrix
        'T': [[1, 0, 1],
              [1, 1, 1],
              [1, 1, 1]],  # Opening times for rooms
        'h': [0, 2, 4]  # number of hours before period
    }
    return small_input


@force_data_format
def build_simple_data(**kwards):
    data = {
        'n': 5,  # 5 exams
        'r': 3,  # 3 rooms
        'p': 3,  # 3 periods
        's': [5, 3, 4, 2, 1],  # number of students per exams
        'c': [5, 4, 1],  # number os seats per rooms
        'conflicts': {0: [3, 4], 1: [3], 2: [0, 1, 2, 4], 3: [0, 2, 3], 4: []},  # Conflicts
        'locking_times': {0: [1], 1: [2], 2: [2]},  # locking times for rooms
        'h': [0, 2, 4]  # number of hours before period
    }
    return data


@force_data_format
def build_smart_random(**kwards):
    """ Generate smart random data
        kwards = {'n': , 'r': ,'p': , 'tseed':, 'w': }
            w = where (0    = not defined
                       1    = Innenstadt,
                       2    = Garching,
                       3    = Hochbrueck,)

    """
    np.random.seed(kwards.get('tseed', 1))
    rd.seed(kwards.get('tseed', 1))
    n, r, p, w = kwards.get('n', 0), kwards.get('r', 0), kwards.get('p', 0), kwards.get('w', ["1", "2", "3", "4", "5", "6", "7"])
    data = {'n': n, 'r': r, 'p': p}

    #create possible number of participants, increase probability that number of participants is between 150 and 300
    num = [i for i in range(10,901)]
    for times in range(1500):
        num.extend([int(i) for i in range(10,150)])
    for times in range(500):
        num.extend([int(i) for i in range(150,301)])

    # get number of students participating
    data['s'] = np.random.choice(num, n)

    # get room capacity from real data
    data['c'] = np.random.choice(num, r)
    data['c'] = sorted(data['c'], reverse=True)

    if kwards.get('locations') == True:
        data['w'] = np.random.choice([["1"], ["2"], ["3"], ["2","3"], ["1","2"], ["1","3"], ["1","2","3"]], n , p=[0.2, 0.1, 0.05, 0.05, 0, 0, 0.6])
        data['location'] = np.random.choice(["1", "2", "3"], r , p=[0.6, 0.35, 0.05])
    
    # hours between starting day and starting periods are fixed equal to 2
    data['h'] = [ 2*l for l in range(p)]
    
    # create a conflict by probybility 1/5
    data['conflicts'] = defaultdict(list)
    for i in range(n):
        data['conflicts'][i] = [ j for j in range(i+1,n) if rd.random() <= 0.05 ]
    
    #close some rooms by probability 1/10
    data['locking_times'] = defaultdict(list)
    for k in range(r):
        data['locking_times'][k] = [ l for l in range(p) if rd.random() <= 0.1 ]

    data = detect_similar_periods(data)
    
    return data


@force_data_format
def build_real_data(**kwards):

    print "Reading data..."
    data = read_real_data()
    
    #data['p'] = kwards.get('p', 40)
    data['p'] = kwards.get('p', 60)

    np.random.seed(kwards.get('tseed', 1))
    rd.seed(kwards.get('tseed', 1))
    
    print data['n']
    print data['r']
    print data['p']

    #close some rooms by probability 10/100
    data['locking_times'] = defaultdict(list)
    for k in range(data['r']):
        data['locking_times'][k] = [ l for l in range(data['p']) if np.random.random(1) <= 0.1 ]
   
    return data


@force_data_format
def build_real_data_sample(**kwards):

    print "Reading data..."
    data = read_real_data()

    n = kwards.get('n', 0)
    r = kwards.get('r', 0)

    np.random.seed(kwards.get('tseed', 1))
    rd.seed(kwards.get('tseed', 1))

    data['p'] = kwards.get('p', 0)


    choose_exams = sorted(np.random.choice(range(data['n']), n, replace=False))
    print choose_exams
    choose_rooms = sorted(np.random.choice(range(data['r']), r, replace=False))

    data['c'] = [data['c'][i] for i in choose_rooms]
    data['n'] = n
    data['s'] = [data['s'][i] for i in choose_exams]
    data['r'] = r

    data['Q'] = [ [data['Q'][i][j] for j in choose_exams] for i in choose_exams]

    #close some rooms by probability 10/100
    data['locking_times'] = defaultdict(list)
    for k in range(data['r']):
        data['locking_times'][k] = [ l for l in range(data['p']) if np.random.random(1) <= 0.1 ]
   
    return data


def detect_similarities(data):
    data = detect_similar_periods(detect_similar_exams(detect_similar_rooms(data)))
    return data


def detect_similar_periods(data):
    roomnumber = {}
    roomcapacities = {}
    for l in range(data['p']):
        roomnumber[l] = sum([1 for k in range(data['r']) if not l in data['locking_times'][k] ])
        roomcapacities[l] = sum([data['c'][k] for k in range(data['r']) if not l in data['locking_times'][k] ])
    
    data['similarp'] = defaultdict(list)
    for l in range(data['p']):
        data['similarp'][l] = [l2 for l2 in range(data['p']) if (roomnumber[l2] <= roomnumber[l]+2 and roomnumber[l2] >= roomnumber[l]-2) and (roomcapacities[l2] <= roomcapacities[l]+100 and roomcapacities[l2] >= roomcapacities[l]-100) ]  
    

    return data


def detect_similar_exams(data):
    # We use an extended notion of similar two exams A and B count as similiar if A has similar or less students participation in a it than B
    
    data['similare'] = defaultdict(list)

    for i in range(data['n']):
        data['similare'][i] = [j for j in range(data['n']) if data['s'][j] >= data['s'][i] -20 and data['s'][j] <= data['s'][i]+20 and data['conflicts'][i] <= data['conflicts'][j] ]  
    

    return data


def detect_similar_rooms(data):
    # We use an extended notion of similar two exams A and B count as similiar if A has similar or less students participation in a it than B
    
    data['similarr'] = defaultdict(list)

    for k in range(data['r']):
        data['similarr'][k] = [k2 for k2 in range(data['r']) if data['c'][k2] <= data['c'][k] +20 and data['c'][k2] >= data['c'][k] -20  ] 
    

    return data


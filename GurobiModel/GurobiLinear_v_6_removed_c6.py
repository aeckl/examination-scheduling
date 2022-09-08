
import sys
import os
PATHS = os.getcwd().split('/')
PROJECT_PATH = ''
for p in PATHS:
    PROJECT_PATH += '%s/' % p
    if p == 'examination-scheduling':
        break
sys.path.append(PROJECT_PATH)

import operator
import itertools
import random
import networkx as nx
import math 
    
from gurobipy import Model, quicksum, GRB, GurobiError
from model.instance import build_random_data

             
    
def build_model(data, n_cliques = 0):
    
    # Load Data Format
    n = data['n']
    r = data['r']
    p = data['p']
    s = data['s']
    c = data['c']
    h = data['h']
    conflicts = data['conflicts']
    locking_times = data['locking_times']
    T = data['T']
    # sR = find_smallest_room_to_fit_in(n=n,s=s,r=r,c=c)
    #print sR
    for k in range(r):
        for l in range(p):
            T[k][l] = 1
    
    model = Model("ExaminationScheduling_v6_removed_c6")
    
    
    print("Building variables...")
    
    # x[i,k,l] = 1 if exam i is at time l in room k
    x = {}
    for i in range(n):
        for k in range(r):
            for l in range(p):
                if T[k][l] == 1:
                    x[i,k,l] = model.addVar(vtype=GRB.BINARY, name="x_%s_%s_%s" % (i,k,l))
    
    # y[i,l] = 1 if exam i is at time l
    y = {}
    for i in range(n):
        for l in range(p):
            y[i, l] = model.addVar(vtype=GRB.BINARY, name="y_%s_%s" % (i,l))
    
    # # help variable z[i,j] and delta[i,j] for exam i and exam j
    # # we are only interested in those exams i and j which have a conflict!
    # z = {}
    # delta = {}
    # for i in range(n):
    #     for j in conflicts[i]:
    #         z[i, j] = model.addVar(vtype=GRB.INTEGER, name="z_%s_%s" % (i,j))
    #         delta[i, j] = model.addVar(vtype=GRB.BINARY, name="delta_%s_%s" % (i,j))
    
    # integrate new variables
    model.update() 

    # adding variables as found in MidTerm.pdf
    print("Building constraints...")    
    
    print("c1: connecting variables x and y")
    for i in range(n):
        for l in range(p):
            model.addConstr( quicksum([ x[i, k, l] for k in range(r) if T[k][l] == 1 ]) <= 12 * y[i, l], "c1a")
            model.addConstr( quicksum([ x[i, k, l] for k in range(r) if T[k][l] == 1 ]) >= y[i, l], "c1b")
            
    print("c2: each exam at exactly one time")
    for i in range(n):
        model.addConstr( quicksum([ y[i, l] for l in range(p) ]) == 1 , "c2")

    """
    Idea:   -instead of saving a conflict Matrix, save Cliques of exams that cannot be written at the same time
            -then instead of saying of one exam is written in a given period all conflicts cannot be written in the same period we could say
            -for all exams in a given clique only one can be written
    """
    
    print("c3: avoid conflicts")
    for i in range(n):
        for l in range(p):
            # careful!! Big M changed!
            model.addConstr(quicksum([ y[j,l] for j in conflicts[i] ]) <= (1 - y[i, l]) * sum(conflicts[i]), "c3")
    
    print("c4: seats for all students")
    for i in range(n):
        model.addConstr( quicksum([ x[i, k, l] * c[k] for k in range(r) for l in range(p) if T[k][l] == 1 ]) >= s[i], "c4")
    
    print("c5: only one exam per room per period")
    for k in range(r):
        for l in range(p):
            if T[k][l] == 1:
                model.addConstr( quicksum([ x[i, k, l] for i in range(n)  ]) <= 1, "c5")
    
   
    # print("c7: resolving the absolute value")
    # for i in range(n):
    #     for j in conflicts[i]:
    #         model.addConstr( z[i, j] <= quicksum([ h[l]*(y[i,l] - y[j,l]) for l in range(p) ]) + delta[i,j] * (2*h[len(h)-1]), "c7a")
    #         model.addConstr( z[i, j] <= -quicksum([ h[l]*(y[i,l]-y[j,l]) for l in range(p) ]) + (1-delta[i,j]) * (2*h[len(h)-1]), "c7b")
    #         model.addConstr( z[i, j] >= quicksum([ h[l]*(y[i,l] - y[j,l]) for l in range(p) ]) , "c7c")
    #         model.addConstr( z[i, j] >= -quicksum([ h[l]*(y[i,l] - y[j,l]) for l in range(p) ]) , "c7d")
            
    
    print("c8: Building clique constraints")
    G = nx.Graph()
    for i in range(n):
        G.add_node(i)
        
    for i in range(n):
        for j in conflicts[i]:
            G.add_edge(i,j)
            
    cliques = nx.find_cliques(G) # generator
    
    for counter, clique in itertools.izip(range(n_cliques), cliques):
        for l in range(l):
            model.addConstr( quicksum([ y[i, l] for i in clique ]) <= 1, "c_lique_%s_%s_%s" % (counter,clique,l))
            print "c_lique_%s_%s_%s" % (counter,clique,l)

    print("All constrained built - OK")



    # objective: minimize number of used rooms
    print("Building Objective...")
    gamma = 1
    obj1 = quicksum([ x[i,k,l] for i,k,l in itertools.product(range(n), range(r), range(p)) if T[k][l] == 1 ]) 
    #obj2 = -quicksum([ z[i,j] for i in range(n) for j in conflicts[i] ])

    #model.setObjective( obj1 + gamma * obj2, GRB.MINIMIZE)
    model.setObjective( obj1, GRB.MINIMIZE)
    # Set Parameters
    print("Setting Parameters...")
    # max presolve agressivity
    #model.params.presolve = 2
    model.params.barconvtol = 1
    model.params.nodelimit = 1
    # Choosing root method 3= concurrent = run barrier and dual simplex in parallel
    #model.params.method = 1

    # return
    return(model)


if __name__ == "__main__":
    
    n = 120
    r = 20
    p = 10

    # generate data
    random.seed(42)
    data = build_random_data(n=n, r=r, p=p, prob_conflicts=0.75)
    exams = [ 'Ana%s' % (i+1) for i in range(n) ]
    rooms = ['MI%s' % (k+1) for k in range(r)]
    
    # Create and solve model
    try:        
        model = build_model(data, n_cliques = 0)        
        
        model.optimize()
        
        #for v in model.getVars():
            #if v.x == 1 and ("x" in v.varName or "y" in v.varName): 
                #print('%s %g' % (v.varName, v.x))

        print('Obj: %g' % model.objVal)

    except GurobiError:
        print('Error reported')
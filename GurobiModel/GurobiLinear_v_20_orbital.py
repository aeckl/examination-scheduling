import sys
import os
PATHS = os.getcwd().split('/')
PROJECT_PATH = ''
for p in PATHS:
    PROJECT_PATH += '%s/' % p
    if p == 'examination-scheduling':
        break
sys.path.append(PROJECT_PATH)

import itertools
import random
import networkx as nx
import math 
from time import time
import timeit
    
from gurobipy import Model, quicksum, GRB, GurobiError, LinExpr
from model.instance import build_random_data

             
    
def build_model(data, n_cliques = 0, verbose = True):
    
    # Load Data Format
    n = data['n']
    r = data['r']
    p = data['p']
    s = data['s']
    c = data['c']
    h = data['h']
    w = data['w']
    location = data['location']
    conflicts = data['conflicts']
    locking_times = data['locking_times']
    T = data['T']
    similarp = data['similarp']
    similare = data['similare']
    similarr = data['similarr']
    
    model = Model("ExaminationScheduling")
    
    
    if verbose:
        print("Building variables...")


    # Calculate Orbits
    rs = 5
    es = 10

    orbit = {}
    for l in range(p):
        for k in range(r):
            if k % rs == 0:
                for i in range(n):
                    if i % es == 0:
                        orbit[i,k,l] = [ (i2,k2,l) for i2 in range(i,min(i+es,n)) for k2 in range(k,min(k+rs,r)) if T[k2][l] == 1 if conflicts[i] <= conflicts[i2] ]


    # x[i,k,l] = 1 if exam i is at time l in room k
    x = {}
    for k in range(r):
        for l in range(p):
            if T[k][l] == 1:
                for i in range(n):
                    if location[k] in w[i]:
                        x[i,k,l] = model.addVar(vtype=GRB.BINARY, name="x_%s_%s_%s" % (i,k,l))
    
    # y[i,l] = 1 if exam i is at time l
    y = {}
    for i in range(n):
        for l in range(p):
            y[i, l] = model.addVar(vtype=GRB.BINARY, name="y_%s_%s" % (i,l))


    #Orbit variable for orbital branching
    o = {}
    for key in orbit:
        if orbit[key]:
            o[key] = model.addVar(vtype=GRB.BINARY, name="o_%s_%s_%s" % (key[0],key[1],key[2]))     

    # integrate new variables
    model.update() 

    for key in orbit:
        if orbit[key]:
            o[key].setAttr("BranchPriority", 1000000)




    start = timeit.default_timer()

    # not very readable but same constraints as in GurbiLinear_v_10: speeded up model building by 2 for small problems (~400 exams) and more for huger problem ~1500 exams
    if verbose:
        print("Building constraints...")    
    
    s_sorted = sorted(range(len(c)), key = lambda k: c[k])
    
    obj = LinExpr()
    sumconflicts = {}
    maxrooms = {}
    for i in range(n):
        sumconflicts[i] = sum(conflicts[i])
        if s[i] <= 50:
            maxrooms[i] = 2
        elif s[i] <= 100:
            maxrooms[i] = 4
        elif s[i] <= 400:
            maxrooms[i] = 9
        elif s[i] <= 700:
            maxrooms[i] = 12
        else:
            maxrooms[i] = 12
        c2 = LinExpr()
        c4 = LinExpr()
        for l in range(p):
            c1 = LinExpr()
            c1 = LinExpr()
            c3 = LinExpr()
            for k in range(r):
                if T[k][l] == 1 and location[k] in w[i]:
                    # print k, c[k], 1-(1/(pow(2,s_sorted.index(k))))
                    #obj.addTerms( 1-(1/(pow(2,s_sorted.index(k)))) , x[i, k, l])
                    obj.addTerms(1, x[i,k,l])
                    c1.addTerms(1, x[i,k,l])
                    c4.addTerms(c[k],x[i,k,l])
            model.addConstr(c1 <= maxrooms[i]* y[i,l], "c1a")
            model.addConstr(c1 >= y[i,l], "C1b")

            for j in conflicts[i]:
                c3.addTerms(1,y[j,l])
            if not conflicts[i]:
                model.addConstr(c3 <= (1 - y[i,l])*sumconflicts[i], "c3")

            c2.addTerms(1,y[i,l])
        model.addConstr( c2 == 1 , "c2")
        model.addConstr(c4 >= s[i], "c4")

    sumrooms = {}
    for l in range(p):
        sumrooms[l] = 0
        cover_inequalities = LinExpr()
        for k in range(r):   
            if T[k][l] == 1:
                sumrooms[l] += 1
                c5 = LinExpr()
                for i in range(n):
                    if location[k] in w[i]:
                        c5.addTerms(1,x[i,k,l])
                model.addConstr( c5 <= 1, "c5")  
                cover_inequalities += c5
        model.addConstr(cover_inequalities <= sumrooms[l], "cover_inequalities")


    for key in orbit:
        if orbit[key]:
            model.addConstr(quicksum( x[i,k,l] for i,k,l in orbit[key]  ) <= o[key]*len(orbit[key]), "symmetrie break")

    # for l in range(p):
    #     print l
    #     for k in range(r):
    #         print k
    #         if T[k][l] == 1:
    #             for i in range(n):
    #                 c6 = LinExpr()
    #                 for i2 in similare[i]:
    #                     for k2 in similarr[k]:
    #                         if k2 >= 0:
    #                             c6.addTerms(1,x[i2,k,l])
    #                 model.addConstr(c6 <= o[i,k,l]*n, "symmetrie break")

    # for i in range(p-2):
    #     for l in range(p):
    #         model.addConstr(y[i,l] <= quicksum( y[i+1,sim] for sim in similarp[l]), "s1")


    model.setObjective( obj, GRB.MINIMIZE)


    #model.write("CPLEX.mps")

    print timeit.default_timer()-start
 
    

    if verbose:
        print("All constrained and objective built - OK")

    

    if not verbose:
        model.params.OutputFlag = 0
    
    # Set Parameters
    #print("Setting Parameters...")
 
    # max presolve agressivity
    #model.params.presolve = 2
    # Choosing root method 3= concurrent = run barrier and dual simplex in parallel
    #model.params.symmetrie = 2
    model.params.method = 3
    #model.params.presolve = 0
    #model.params.MIPFocus = 1

    model.params.OutputFlag = 1
    #model.params.MIPFocus = 1

    model.params.heuristics = 0
    model.params.cuts = 0


    return(model)



if __name__ == "__main__":
    
    n = 200
    r = 30
    p = 30  

    # generate data
    random.seed(42)
    data = build_random_data(n=n, r=r, p=p, prob_conflicts=0.75)
    exams = [ 'Ana%s' % (i+1) for i in range(n) ]
    rooms = ['MI%s' % (k+1) for k in range(r)]
    
    # Create and solve model
    t = time()
    try:        
        model = build_model(data, n_cliques = 30)        
        
        model.optimize()
        
        for v in model.getVars():
            if v.x == 1 and ("x" in v.varName or "y" in v.varName): 
                print('%s %g' % (v.varName, v.x))

        print('Obj: %g' % model.objVal)
    except GurobiError:
        print('Error reported')
    t = time() - t
    print('Runtime: %0.2f s' % t)
    
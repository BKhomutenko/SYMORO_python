# -*- coding: utf-8 -*-
"""
Created on Mon May 13 21:35:46 2013

@author: Bogdqn
"""


from sympy import pi,simplify
from symoro import *
from RX90 import *

def parcour(i,j):
    u = []
    v = []
    while i != -1:
        u.append(i)
        i = ant[i]
    while j != -1:
        v.append(j)
        j = ant[j]
    k = max(set(u) & set(v))
    return k

def compute_transform_fast(frames, fast_form = True,sym_dict = {},trig_dict = {}):
    #identity matrix as initial transformation
    T_prev = eye(4)
    #computing DGM
    i = frames[1]-1
    def terminate():
        return (i == frames[0]-1)
    while not terminate():
        index_list = []
        T = eye(4)
        while True:
            T = transform(theta[i],r[i],alpha[i],d[i],gamma[i],b[i])*T
            mat_trigsimp(T)
            index_list.append(i)
            i_prev = i
            i = ant[i]
            if alpha[i_prev] != 0 or terminate():
                break
        T = mat_trig_replace(T,trig_dict,index_list,theta,alpha,gamma)
        T_res = T*T_prev
        #make substitution with saving the var to the dictionary
        if fast_form:
            mat_sym_replace(T_res,sym_dict,'U',i+1)
        T_prev = T_res
    return T_res

#todo check trig subs
sydi = {}
Transforms = (0,6)
#print parcour(3,1)
T_res = compute_transform_fast(Transforms,fast_form = True, sym_dict = sydi)
#making the substitution
print 'unfolded DGM:'
name = 'T{0}{1}'.format(Transforms[0],Transforms[1])
for i2 in range(4):
    for i1 in range(3):
        print '{2}{0}{1}'.format(i1+1,i2+1,name),'=', unfold(T_res[i1,i2],sydi)
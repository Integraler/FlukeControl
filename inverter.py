#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 15:24:10 2020

@author: benjamin
"""

import numpy as np

caldata_raw = np.genfromtxt('PressureCalib_2020-07-02_14:32:28.txt', skip_header = 1)
for i in range(0, len(caldata_raw)):
    caldata_raw[i][0] = caldata_raw[i][0]*(-1)
np.savetxt('test.txt',caldata_raw,'%1.4f')    

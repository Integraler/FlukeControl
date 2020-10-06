# -*- coding: utf-8 -*-
"""
Created on Mon Jul 3 10:07:30 2020

@author: Benjamin Kraus
"""


import numpy as np
import serial
import pyvisa
from time import sleep

rm = pyvisa.ResourceManager()
resourcelist = rm.list_resources()
dev = rm.open_resource('ASRLCOM7::INSTR')
for i in range(0,100):
    print(dev.query('MEAS:VOLT? 10'))
    sleep(1)
    
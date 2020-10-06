#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  8 10:09:33 2020
Steuerung Druckkalibrator Fluke 6720-A
@author: benjamin
"""

# Lade Pythonpakete
try:
    import tkinter as tk
    import tkinter.scrolledtext as tkst
except ImportError:
    import Tkinter as tk
from tkinter import ttk
import pyvisa
import serial
from time import sleep
import threading
from os import getcwd
import time
import binascii
import numpy as np
import libscrc
from functools import partial
import datetime
from os import getcwd
from tkinter import filedialog
import the_ghost_of_the_pressure_calibrator as KalibScript

# Verbindung zum Gerät
class MAINGUI(tk.Tk):
    """Rotor Datenerfassungsprogramm"""

    def __init__(self, **kwargs):
        tk.Tk.__init__(self, **kwargs)
        self.title('Software 6720-A')
        # define Devices
        self.calibrationdevice = Calibration_device(self)
        self.measuredevice = Measure_device(self)
        self.einzelzeile = []
        self.file_name = ''
        # widget definitions ===================================
        self.initUI()
     
    def initUI(self):            
        note = ttk.Notebook(self)
        ConnectProperties = tk.Frame(note)
        CalibProperties = tk.Frame(note)
        CalibControl = tk.Frame(note)
        CalibResults = tk.Frame(note)
        CalibReport = tk.Frame(note)
        note.add(ConnectProperties, text='Verbindungseinstellungen')
        note.add(CalibProperties, text='Kalibratorsteuerung')
        note.add(CalibControl, text='Kalibrierablauf')
        note.add(CalibResults, text='Ergebnissanzeige')
        note.add(CalibReport, text='Kalibrierbericht')
        note.grid(row=0, column=0, sticky='nwes')
        
        # Serialchoice and Connection
        self.label_serialchoice = tk.Label(ConnectProperties, text='Schnittstellenauswahl').grid(row=0, column=0, columnspan=2)
        
        self.label_measure_device = tk.Label(ConnectProperties, text='Messgerät').grid(row=1,column=0)
        self.frame_measure_device = Frame_SerialInput(ConnectProperties)
        self.frame_measure_device.grid(row=2, column=0)
        
        self.label_calibration_device = tk.Label(ConnectProperties, text='Kalibrator').grid(row=1,column=1)
        self.frame_calibration_device = Frame_SerialInput(ConnectProperties)
        self.frame_calibration_device.grid(row=2, column=1)
        
        self.bt_connect = tk.Button(ConnectProperties, text='Verbindung aufbauen', command=self.connect, width=20)
        self.bt_connect.grid(row=3, column=0, columnspan=2)
        
        # Settings Calibrationdevice
        self.label_calibrationsetting = tk.Label(CalibProperties, text='Einstellung Fluke 6720-A').grid(row=0, column=0)
        self.frame_calibrationsetting = Frame_CalibrationSetting(CalibProperties,self)
        self.frame_calibrationsetting.grid(row=1, column=0)
        
        # Calibration Controll
        self.label_calibrationControl = tk.Label(CalibControl, text='Kalibriermenu Fluke 6720-A').grid(row=0,column=0)
        self.Frame_calibrationControl = Frame_CalibrationControl(CalibControl,self).grid(row=1, column=0)

        # Calibration Results
        self.resultarea = tkst.ScrolledText(
            master = CalibResults,
            wrap   = tk.WORD,
            height = 10
        )
        self.resultarea.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.resultarea.configure(state=tk.DISABLED)
        
        # Calibration Report settings
        self.Frame_calibrationReport = Frame_CalibrationReport(CalibReport,self).grid(row=1, column=0)
        
    def openfile(self):
        self.resultarea.configure(state=tk.NORMAL)
        if self.file_name != '':
            self.resultarea.delete(1.0, tk.END)
            with open(self.file_name) as _file:
                self.resultarea.insert(1.0, _file.read())
            self.resultarea.configure(state=tk.DISABLED)
            self.resultarea.yview_moveto(1)
            
            
    def connect(self):
        self.measuredevice.open_connection(self)
        self.calibrationdevice.open_connection(self)
        # try:
        unit = self.calibrationdevice.get_Unit()
        slewrate = self.calibrationdevice.get_slewrate()
        self.frame_calibrationsetting.Unit.set(unit.replace('\r\n', ''))
        self.frame_calibrationsetting.slewrate.set(slewrate)
        modulenames = []
        for i in range(1,5):
            name = self.calibrationdevice.getModulName(i)
            modulenames.append(name.replace('\r\n',''))
            self.frame_calibrationsetting.Modul.append(name.replace('\r\n',''))
            self.frame_calibrationsetting.ModulMenu['values'] = modulenames                
        # except:
        #     print('Fehler beim auslesen der Kalibratoreinstellungen')
        
class Frame_SerialInput(tk.Frame):
    def __init__(self, master, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)
        self.initUI()
        
    def initUI(self):    
        self.label_comport = tk.Label(self, text="COM")
        self.label_comport.grid(row=0, column=0)
        self.comport = tk.StringVar()
        self.comport.set('COM1')
        self.ports = ['COM1', "COM2", "COM3", "COM4", "COM5", "COM6", "USB0", "USB1"]
        self.ComMenu = ttk.Combobox(self, textvariable=self.comport, values=self.ports, justify='right', width=10)
        self.ComMenu.grid(row=1, column=0)
        
        self.label_baud = tk.Label(self, text="BAUD")
        self.label_baud.grid(row=0, column=1)
        self.baudrate = tk.StringVar()
        self.baudrate.set('9600')
        self.baud = ["9600", "19200", "38400"]
        self.BaudMenu = ttk.Combobox(self, textvariable=self.baudrate, values=self.baud, justify='right', width=10)
        self.BaudMenu.grid(row=1, column=1)

class Frame_CalibrationSetting(tk.Frame):
    def __init__(self, masterframe, master, **kwargs):
        tk.Frame.__init__(self, masterframe, **kwargs)
        self.Unit = tk.StringVar()
        self.slewrate = tk.DoubleVar()
        self.pressvalue = tk.StringVar()
        self.initUI(master)

    def initUI(self,master):        
        self.label_Unit = tk.Label(self, text="Einheit ").grid(row=0, column=0)
        self.Unit.set('PA')
        self.choice_Unit = ["PA", "KPA", "MPA", "BAR"]
        self.box_Unit = ttk.Combobox(self, textvariable=self.Unit, values=self.choice_Unit, justify='right', width=10)
        self.box_Unit.grid(row=0, column=1)
        
        self.label_slewrate =tk.Label(self, text='Anstiegsrate').grid(row=1, column=0)
        self.slewrate.set(5000)
        self.entry_slewrate = tk.Entry(self, text='', textvariable=self.slewrate, width=11, justify='right')
        self.entry_slewrate.grid(row=1, column=1)
        
        self.label_pressvalue =tk.Label(self, text='Solldruck').grid(row=2, column=0)
        self.pressvalue.set(5000)
        self.entry_pressvalue = tk.Entry(self, text='', textvariable=self.pressvalue, width=11, justify='right')
        self.entry_pressvalue.grid(row=2, column=1)
        
        self.label_Modus = tk.Label(self, text="Modusauswahl")
        self.label_Modus.grid(row=3, column=0)
        self.Modusname = tk.StringVar()
        self.Modusname.set('AUTO')
        self.Modus = ["AUTO", "FAST", "FEST"]
        self.ModusMenu = ttk.Combobox(self, textvariable=self.Modusname, values=self.Modus, justify='right', width=10)
        self.ModusMenu.grid(row=3, column=1)
        self.ModusMenu.bind('<<ComboboxSelected>>', self.callback)

        self.label_Modul = tk.Label(self, text="Modul")
        self.label_Modul.grid(row=3, column=2)
        self.Modulname = tk.StringVar()
        self.Modul = []
        self.Modulname.set('')
        self.ModulMenu = ttk.Combobox(self, textvariable=self.Modulname, values=self.Modul, justify='right', width=10)
        self.ModulMenu.grid(row=3, column=3)
        self.ModulMenu.configure(state='disabled')
        
        self.label_Mode = tk.Label(self, text="Modusauswahl")
        self.label_Mode.grid(row=3, column=0)
        self.Modename = tk.StringVar()
        self.Modename.set('Relativ')
        self.Mode = ["Absolut", "Relativ"]
        self.ModeMenu = ttk.Combobox(self, textvariable=self.Modename, values=self.Mode, justify='right', width=10)
        self.ModeMenu.grid(row=4, column=1)
        
        
        CreateToolTip(self.label_Modus, '''Das Gerät wählt das aktive Druckmessmodul auf die folgenden Arten aus:\n
            Auto – Dies ist die Standardeinstellung. Das Gerät wählt das Modul mit dem
            kleinsten Druckbereich aus, der zur Messung des aktuellen Drucks ausreicht.\n
            Schnell – Das Gerät wählt das Modul mit dem kleinsten Druckbereich aus, der
            zur Messung des Sollwerts ausreicht. Bei dieser Methode wechselt das Gerät
            beim Ansteigen des Drucks nicht zwischen Bereichen, sondern wählt direkt den
            erforderlichen Bereich aus und behält diesen bei.\n
            Fest – Das Gerät bleibt immer in dem vom Benutzer ausgewählten Bereich. Bei
            dieser Methode kann kein Sollwert eingegeben werden, der außerhalb des
            Messbereichs des ausgewählten Moduls liegt.''')
        
        self.bt_setsettings = tk.Button(self, text='Übernehmen', command=partial(self.setsettings,master)).grid(row=10, column=0)
        self.bt_setsettings = tk.Button(self, text='Regeln', command=partial(self.startControllMode,master)).grid(row=10, column=1)
        self.bt_setsettings = tk.Button(self, text='Entlüften', command=partial(self.startVentMode,master)).grid(row=10, column=2)
        
    def setsettings(self,master):
        master.calibrationdevice.set_Unit(self.Unit.get())
        master.calibrationdevice.set_slewrate(self.slewrate.get())
        master.calibrationdevice.set_PressureLevel(self.pressvalue.get())
        master.calibrationdevice.setInstrPresMode(self.ModeMenu.get())
        # if self.Modusname.get() != 'FEST':
        #     master.calibrationdevice.controllingMode(self.Modusname.get())
        # else:
        #     index = self.Modul.index(self.Modulname.get())
        #     master.calibrationdevice.controllingMode(str(index))
        
    def startControllMode(self,master):
        master.calibrationdevice.set_PressureLevel(self.pressvalue.get())
        master.calibrationdevice.controllingMode()

    def startVentMode(self,master):
        master.calibrationdevice.ventMode()

    def callback(self,master):
        if self.Modusname.get() == 'AUTO':
            self.Modulname.set('autom. Auswahl')
            self.ModulMenu.configure(state='disabled')
        elif self.Modusname.get() == 'FAST':
            self.Modulname.set('autom. Auswahl')
            self.ModulMenu.configure(state='disabled')
        elif self.Modusname.get() == 'FEST':
            self.ModulMenu.configure(state='normal')

class Frame_CalibrationControl(tk.Frame):
    def __init__(self, masterframe, master, **kwargs):
        tk.Frame.__init__(self, masterframe, **kwargs)
        self.calstep_list = []
        self.calstep_label = []
        self.frame_setting = tk.Frame(self)
        self.frame_setting.grid(row=0, column=0)
        self.frame_button = tk.Frame(self)
        self.frame_button.grid(row=1, column=0,sticky='NW')
        self.frame_measpoints = tk.Frame(self)
        self.frame_measpoints.grid(row=2, column=0,sticky='NW')
        self.frame_process = tk.Frame(self)
        self.frame_process.grid(row=3, column=0, sticky='NW')
        self.test_process = Controller(self.startcalibration, args=(master,), name='test_process')
        self.initUI(master)

    def initUI(self, master):  
        self.label_calsteps = tk.Label(self.frame_setting, text='Schritte').grid(row=0,column=0)
        self.value_calsteps = tk.StringVar()
        self.entry_calsteps = tk.Entry(self.frame_setting, textvariable=self.value_calsteps, justify='right').grid(row=0, column=1)
        self.unit_calsteps_variable = tk.StringVar()
        self.unit_calsteps = tk.Label(self.frame_setting, text='Einheit')
        self.unit_calsteps.grid(row=0,column=2)
        self.boolean_hysterese = tk.BooleanVar()
        self.check_calsteps = tk.Checkbutton(self.frame_setting,text='Hysterese',variable=self.boolean_hysterese).grid(row=0, column=3)

        self.label_measpoint = tk.Label(self.frame_setting, text='Einzelmessungen').grid(row=1,column=0)
        self.value_measpoint = tk.IntVar()
        self.entry_measpoint = tk.Entry(self.frame_setting, textvariable=self.value_measpoint, justify='right').grid(row=1, column=1)    
        
        self.bt_set = tk.Button( self.frame_button, text='Übernehmen', command=self.setCalibrationSteps)
        self.bt_set.grid(row=5,column=0)
        self.bt_start = tk.Button( self.frame_button, text='Starten', command=self.test_process.run)
        self.bt_start.grid(row=5,column=1)
        self.bt_abort = tk.Button( self.frame_button, text='Abbruch', command=partial(self.abort,master))
        self.bt_abort.grid(row=5, column=2)
        
        self.text_waiting = tk.StringVar()
        self.text_waiting.set('0')
        self.label_waiting = tk.Label(self.frame_process, text='', textvariable=self.text_waiting).grid(row=12,column=0,columnspan=5)
        self.progress_waiting = ttk.Progressbar(self.frame_process, orient="horizontal",length=200, mode="determinate", maximum = 30)
        self.progress_waiting.grid(row=13,column=0,columnspan=5)
        self.text_state = tk.StringVar()
        self.text_state.set('Warten auf Start')
        self.label_state = tk.Label(self.frame_process, text='', textvariable=self.text_state)
        self.label_state.grid(row=13,column=5)
        
    def setCalibrationSteps(self):
        self.calstep_list = []
        steps = self.value_calsteps.get()
        steps = steps.split(',')
        i=0
        if len(self.calstep_label) > 0:
            for ele in self.calstep_label:
                ele.grid_forget()

        for element in steps:
            test = tk.Label(self.frame_measpoints,text=element,width=10)
            test.grid(row=10,column=i)
            self.calstep_label.append(test)
            self.calstep_list.append(float(element))
            i+=1
        if self.boolean_hysterese.get():
            i=0
            steps.reverse()
            for element in steps:
                test = tk.Label(self.frame_measpoints,text=element,width=10)
                test.grid(row=11,column=i)
                self.calstep_label.append(test)
                self.calstep_list.append(float(element))
                i+=1
        
    def startcalibration(self, master):
        self.abortflag = False
        self.bt_start.config(state = tk.DISABLED)
        self.calibtest = CalibrationTest(master)
        self.calibtest.start(master,self,self.value_measpoint.get(),True,self.calstep_list)

    def abort(self,master):
        self.abortflag = True
        self.bt_start.config(state = tk.NORMAL)        
        self.text_waiting.set('0')
        self.progress_waiting['value'] = 0
        master.calibrationdevice.ventMode()
        self.text_state.set('Abbruch')

class Frame_CalibrationReport(tk.Frame):
    def __init__(self, masterframe, master, **kwargs):
        tk.Frame.__init__(self, masterframe, **kwargs)
        self.initUI(master)
        
    def initUI(self,master):  
        
        self.frame_CalculationSetting = tk.Frame(self)
        self.frame_CalculationSetting.grid(row=1, column=3)
       
        self.listbox1 = tk.Listbox(self, selectmode="extended")
        self.listbox1.grid(row=0, column=0, rowspan=2)
        self.listbox2 = tk.Listbox(self, selectmode="extended")
        self.listbox2.grid(row=0, column=2, rowspan=2)
        
        copy12 = partial(self.copy, self.listbox1, self.listbox2)
        copy21 = partial(self.copy, self.listbox2, self.listbox1)
        button = tk.Button(self, text=">>", command=copy12)
        button.grid(row=0, column=1)
        button = tk.Button(self, text="<<", command=copy21)
        button.grid(row=1, column=1)
        
        bt_openfile = tk.Button(self, text = 'Datei laden', command = self.openfile)
        bt_openfile.grid(row=0, column=3)
        
        tk.Label(self.frame_CalculationSetting,text='Bearbeiter:',justify='left').grid(row=0, column=0)
        tk.Label(self.frame_CalculationSetting,text='Sensorname:').grid(row=1, column=0)
        tk.Label(self.frame_CalculationSetting,text='Polynom:').grid(row=2, column=0)
        tk.Label(self.frame_CalculationSetting, text='Einzelmessungen').grid(row=3,column=0)
        tk.Label(self.frame_CalculationSetting,text='Referenz:').grid(row=4, column=0)
        
        self.value_staff = tk.StringVar()
        tk.Entry(self.frame_CalculationSetting, textvariable=self.value_staff, justify='right').grid(row=0, column=1)        
        self.value_sensorname = tk.StringVar()
        tk.Entry(self.frame_CalculationSetting, textvariable=self.value_sensorname, justify='right').grid(row=1, column=1)        
        self.value_poly = tk.StringVar()
        self.value_poly.set('linear')
        self.polyOptions = ['linear','quadratic','cubic']
        self.poly_Combobox = ttk.Combobox(self.frame_CalculationSetting, textvariable=self.value_poly, values=self.polyOptions, justify='right', width=10)
        self.poly_Combobox.grid(row=2, column=1)       
        
        self.value_measpoint = tk.IntVar()
        self.entry_measpoint = tk.Entry(self.frame_CalculationSetting, textvariable=self.value_measpoint, justify='right').grid(row=3, column=1)    
        
        self.Reference = tk.StringVar()
        self.Reference.set('')
        self.ReferenceOptions = []
        self.Reference_Combobox = ttk.Combobox(self.frame_CalculationSetting, textvariable=self.Reference, values=self.ReferenceOptions, justify='right', width=10)
        self.Reference_Combobox.grid(row=4, column=1)
        self.Reference_Combobox.configure(state='disabled')
        
        bt_start = tk.Button(self.frame_CalculationSetting, text = 'Report erstellen', command = self.generatereport)
        bt_start.grid(row=5, column=0)
    
    def copy(self, listbox1, listbox2):
        inertiallist_index = []
            
        text_listbox1 = []
        for i in self.inertiallist:
            text_listbox1.append(i)
        text_listbox2 = []
        
        alist = listbox1.get(0,'end')
        
        for index in reversed(listbox1.curselection()):
            inertiallist_index.append(self.inertiallist.index(listbox1.get(index)))
            
        for index in list(listbox2.get(0,'end')):
            inertiallist_index.append(self.inertiallist.index(index))
            
        inertiallist_index = sorted(inertiallist_index, reverse=True)      
            
        for index in inertiallist_index:
            del text_listbox1[index]
            text_listbox2.append(self.inertiallist[index])
            
        listbox1.delete(0,'end')
        listbox2.delete(0,'end')
        
        listbox1.insert('end',*text_listbox1)
        listbox2.insert('end',*reversed(text_listbox2))       
               
    def generatereport(self):
        counter = 0
        spalten = []
        for index in self.listbox2.get(0,'end'):
            spalten.append(self.inertiallist.index(index))
                  
        for element in spalten:
            Kal = KalibScript.Kalibration()
            Kal.counter = counter
            Kal.sensorfile = self.path_coeff
            Kal.referencefile = self.path_coeff
            Kal.referenceblock = self.value_measpoint.get()
            Kal.polyorder  = self.value_poly.get()
            Kal.sensortype = "Druck"
            Kal.referencetype = "Block"
            Kal.referenzspalte = 0
            Kal.bearbeiter = self.value_staff.get()
            Kal.sensorspalte = element
            Kal.sensorname = self.value_sensorname.get()+ ' ' + str(counter)
            Kal.setup = "Kalibrator Kalt, Ref Block"
            counter+=1
            Kal.run()
            
    def openfile(self):
        path = getcwd()
        self.path_coeff = filedialog.askopenfilename(initialdir=path, title='Konfig einlesen',
                                                    filetypes=(('txt files', '*.txt'), ('all files', '*,*')))
        with open(self.path_coeff) as _file:
            self.names = _file.readlines(1)
        self.names = str(self.names[0])
        self.names = self.names.split(' ')
        self.importfile = np.genfromtxt(self.path_coeff, skip_header=1, 
                                  delimiter=' ', names=self.names)
        
        self.listbox1.delete(0,'end')
        self.listbox1.insert('end',*self.names)        
        self.Reference_Combobox['values'] = self.names
        self.inertiallist = list(self.listbox1.get(0,'end'))
        self.Reference_Combobox.configure(state='normal')

class Measure_device():
    def __init__(self, master):
        self.process = Controller(self.gatherdata, args=(master,), name='process')
        
    def open_connection(self, master):
        self.ser = serial.Serial()
        self.ser.port = "/dev/tty" + master.frame_measure_device.comport.get()
        self.ser.baudrate = master.frame_measure_device.baudrate.get()
        self.ser.setDTR(0)
        self.ser.close()
        self.ser.open()
        self.check_gather = True
        self.process.run()
        
    def gatherdata(self,master):
        zeile = self.ser.read_until(terminator=b'\xaa\x55')
        while self.ser.in_waiting < 500:
            sleep(0.0001)
        zeile = self.ser.read_until(terminator=b'\xaa\x55')
        self.data = []
        for n in range(len(zeile) // 2):
            self.data.append(int(binascii.hexlify(zeile[n * 2:n * 2 + 2]), 16))
        self.einzelzeile = np.asarray(self.data, dtype=np.float16)
        Kennung = zeile[0]
        datalength = (zeile[0]+4)*2
        zeile = self.ser.read(datalength)
        while self.check_gather:
            self.data = []
            zeile = []
            zeile = self.ser.read(datalength)
            checkline = zeile[0:len(zeile)-4]
            crc16send = zeile[len(zeile)-4:len(zeile)-2]
            crc16 = libscrc.modbus(checkline)
            crc_check = crc16 == int(binascii.hexlify(crc16send),16) 
            for n in range(len(zeile) // 2):
                self.data.append(int(binascii.hexlify(zeile[n * 2:n * 2 + 2])[0:4],16))
            if crc_check == False:
                self.data[len(self.data)-1] = '43690' 
            master.einzelzeile = self.data
            
class Calibration_device():
    def __init__(self, master):    
        self.rm = pyvisa.ResourceManager('@py')
        self.kalib = ''
              
    def open_connection(self, master):
        # self.ser = serial.Serial()
        # self.ser.port = '/dev/tty' + master.frame_calibration_device.comport.get()
        # self.ser.baudrate = master.frame_calibration_device.baudrate.get()
        # self.ser.setDTR(0)
        # self.ser.open()
        port = '/dev/tty' + master.frame_calibration_device.comport.get()
        resourcelist = self.rm.list_resources()
        self.kalib = self.rm.open_resource(('ASRL' + port + '::INSTR'))
      
    def set_Unit(self, string):
        # Setzen der Einheit
        self.kalib.write('UNIT:PRES ' + string)
        
    def get_Unit(self):
        unit = str(self.kalib.query('UNIT:PRES?'))
        return unit
        
    def set_slewrate(self,slewrate:(float) = 5000):
        # Setzen der Anstiegsrate  
        self.kalib.write('SOUR:PRES:SLEW ' + str(slewrate))

    def get_slewrate(self):
        slewrate = float(self.kalib.query('SOUR:PRES:SLEW?'))
        return slewrate
        
    def set_PressureLevel(self, level):
        # Setzen des Sollwertes
        self.kalib.write('SOUR:PRES:LEV:IMM:AMPL ' + str(level))
        
    def controllingMode(self, 
                        module: (str) = 'AUTO'):
        # Starte Regelung
        self.kalib.write('SENS:PRES:MOD ' + module)
        self.kalib.write('OUTP:PRES:MODE CONT')
    
    def readycheck(self):
        # Prüfe ob Regelung abgeschlossen        
        if int(self.kalib.query('STAT:OPER:COND?')) == 16:
            return True
        else:
            return False
        
    def measureMode(self):
        # Starte Messung
        self.kalib.write('OUTP:PRES:MODE MEAS')
        
    def getPressureData(self):
        # Messwertaufnahme
        p = float(self.kalib.query('MEAS:PRES?')) # Druckmessung
        sigp = float(self.kalib.query('MEAS:PRES:UNC?')) # Druckmessung   
        return p, sigp
            
    def ventMode(self):
        # Entlüfte Kalibrator
        self.kalib.write('OUTP:PRES:MODE VENT')
        
    def getModulName(self,Modulenumber):
        name = self.kalib.query('SENS:PRES:MOD'+ str(Modulenumber) +':NAME?')
        return name
            
    def setInstrPresMode(self,mode):
        # Legt Instrumenten Messmodi fest
        print(mode)
        if mode == 'Absolut':
            mode = 'ABS'
        elif mode == 'Relativ':
            mode = 'GAUG'
        else:
            print('Falscher Modus')
        self.kalib.write('SENS:PRES:MODE ' + str(mode))

class CalibrationTest():
    def __init__(self, master):
        
        self.date = str(datetime.datetime.now())
        self.name = 'PressureCalib_' + self.date.split(' ')[0] + '_'+ self.date.split(' ')[1][0:8] +'.txt'
        self.file = self.name
        master.file_name = self.file
        self.calib_data = []
        filehead = ['Druck','Unsicherheit']
        for i in range(0,len(master.einzelzeile)):
            filehead.append('Kanal'+str(i))
        with open(self.file,'a') as _file:
            for ele in filehead:
                _file.write(ele + ' ')
            _file.write('\n')
        
    def start(self, master, progress,
                    count: (int) = 1, 
                    device: (bool) = False,
                    calstep: (list) = []):
        
        k = 0    
        for element in calstep:
            progress.label_state.config(bg='yellow')
            progress.text_state.set('Druckregelung')
            master.calibrationdevice.set_PressureLevel(element)
            master.calibrationdevice.controllingMode()
            i = 0
            while i != 31:
                if progress.abortflag == True:
                    return
                if master.calibrationdevice.readycheck():
                    progress.text_state.set('Halten')
                    progress.text_waiting.set(str(i))
                    progress.progress_waiting['value'] = i
                    i += 1
                    sleep(1)
                else:
                    progress.text_state.set('Druckregelung')
                    i = 0
                    progress.text_waiting.set(str(i))
                    progress.progress_waiting['value'] = i
            progress.text_state.set('Messung')
            master.calibrationdevice.measureMode()
            for i in range(1,count+1):
                if progress.abortflag == True:
                    return
                [p, sigp] = master.calibrationdevice.getPressureData()
                self.calib_data = []
                self.calib_data = [p, sigp]
                if device:
                    device_data = master.einzelzeile
                    for j in range(0,len(device_data)):
                        self.calib_data.append(device_data[j])
                self.calib_data = np.asarray(self.calib_data)
                with open(self.file,'a') as _file:
                    np.savetxt(_file, np.atleast_2d(self.calib_data), fmt='%4s')
                master.openfile()
                sleep(0.5)
            progress.calstep_label[k].config(bg='green')
            k += 1
        master.calibrationdevice.ventMode()
        progress.text_state.set('Abgeschlossen')
        progress.label_state.config(bg='green')
        
class Controller(threading.Thread):
    """Routine für die Initialisierung aller Threads"""
    def __init__(self, func, args, name, kwargs=None):
        threading.Thread.__init__(self)
        self.func = func
        self.name = name
        self.args = args or []
        self.kwargs = kwargs or {}
        self.running = False

    def stop(self):
        self.running = False

    def restart(self):
        self.running = True

    def run(self):
        t = threading.Thread(target=self.func, args=self.args, name=self.name, kwargs=self.kwargs)
        t.setDaemon(True)
        t.start()

        while self.running:
            sleep(0.05)

class Textoutput(tk.Toplevel):
    def __init__(self, **kw):
        tk.Frame.__init__(self, **kw)
        self.text_widget = ScrolledText.ScrolledText(    
            master = self,
            wrap   = tk.WORD,
            ).pack()
        self.text_widget.insert(tk.INSERT, """\Integer posuere erat a ante venenatis dapibus""")
        
class CreateToolTip(object):
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
    def enter(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background='lightgrey', relief='solid', borderwidth=1,
                       font=("times", "10", "normal"))
        label.pack(ipadx=1)
    def close(self, event=None):
        if self.tw:
            self.tw.destroy()

if __name__ == '__main__':
    app = MAINGUI()
    app.columnconfigure(0, weight=1)
    app.rowconfigure(0, weight=1)
    app.mainloop()

    


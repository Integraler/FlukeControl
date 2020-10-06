#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 15:41:11 2020

@author: benjamin
"""


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 14:17:33 2019

@author: philipp
"""

import matplotlib

from pylatex import Document, Section, Subsection, LongTable, Figure, Command, NoEscape, Math
matplotlib.use('Agg')  # Not to use X server. For TravisCI.

import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from UliEngineering.Physics.RTD import pt100_temperature as pt100
from UliEngineering.Physics.RTD import pt1000_temperature as pt1000



class Kalibration():
    """Kalibriert Sensoren gegen einen Referenzsensor"""
    def __init__(self):
        self.sensorfile = ""
        self.referencefile = ""
        self.polyorder = ""
        self.sensortype = ""
        self.referenztype = ""
        self.referenceblock = ""
        self.Sensordata = ""
        self.Referencedata = ""
        self.sensorspalte = 0
        self.referenzspalte = 0
        self.bearbeiter = "B. Kraus"
        self.sensorname = ""
        self.rsme = 0
        self.setup = ""
        self.counter = 0
        
    def sensordaten_einlesen(self):
        """Liest Daten aus der Spalte eines txt Dokuments aus und erstellt Kanalklassen"""
        self.caldata = []
        self.caldata_raw = np.genfromtxt(self.sensorfile, usecols = np.asarray(self.sensorspalte), skip_header = 1)
        for ele in self.caldata_raw:
            self.caldata.append(int(ele))
        self.Sensordata = Channel()
    
    def referenzdaten_einlesen(self):
        """Liest Daten des Referenzsensor aus txt Dokument und erstellt Referenzklasse"""
        self.refdata = np.genfromtxt(self.referencefile, skip_header=1, usecols=np.asarray(self.referenzspalte))
        self.Referencedata = Reference()
    
    def sensorverarbeiten(self):
        """Sucht Plateaus in den Rohdaten und mittelt dort"""
        self.Sensordata.justmw(self)
        
    def referenz_verarbeiten(self, kalibrieren = True):
        """Mittelt Daten der Referenzsensoren, in Blöcken der Länge von referenceblock (Vorgabe 50) und kalibriert sie""" 
        self.Referencedata.mittelwerte(self)
        if kalibrieren == True:
            self.Referencedata.calibrate(self)
        
    def fitsensor(self):
        self.Sensordata.calibrate(self)
        self.Sensordata.rsme(self)
        
    def report(self):
        geometry_options = {"tmargin": "1cm", "lmargin": "2cm"}
        doc = Document(page_numbers= False, geometry_options=geometry_options)
        with doc.create(Section('Kalibration ' + self.sensorname, numbering = False)):
            with doc.create(LongTable("l l")) as data_table:
                data_table.add_row(['Kalibration durchgeführt von ', self.bearbeiter])
                data_table.add_row(['Datum', NoEscape(r'\today')])
                data_table.add_row(['Sensortyp ', self.sensortype])
                data_table.add_row(['Sensorbezeichnung', self.sensorname])
                data_table.add_row(['Aufbau: ', self.setup])
                data_table.add_row(['Fitfunktion: ', self.Sensordata.fitfunction])
                counter = 0
                if self.sensortype == 'NTC':
                    data_table.add_row(['Referenztemperatur ', self.ntcrefT])
                    data_table.add_row(['Referenzwiderstand', self.ntcrefR])
                for element in self.Sensordata.best:
                    data_table.add_row(['A' + str(counter),str(element)])
                    counter+=1   
                data_table.add_row(['R²: ', self.rsme]) 
                data_table.add_row(['2sigma',2*np.std(self.Sensordata.fit_fkt(self.Sensordata.mw, *self.Sensordata.best)-self.Referencedata.caldat)])
            plt.plot(self.Sensordata.fit_fkt(self.Sensordata.mw, *self.Sensordata.best), self.Sensordata.mw,'+-')
            plt.ylabel('Digit')
            plt.xlabel('Druck in Pa')
            plt.title('Fitfunktion')
            with doc.create(Figure(position='htbp')) as plot:
                        plot.add_plot(width=NoEscape(r'0.7\textwidth'),dpi=300)
            plt.close()
            plt.plot(self.Referencedata.caldat,self.Sensordata.fit_fkt(self.Sensordata.mw, *self.Sensordata.best)-self.Referencedata.caldat,'+-')        
            plt.title('Abweichung vom Fit')
            plt.ylabel('dp')
            plt.xlabel('Druck in Pa')
            with doc.create(Figure(position='htbp')) as plot:
                        plot.add_plot(width=NoEscape(r'0.7\textwidth'),dpi=300)
            plt.close()
        with doc.create(Section('Gemittelte Rohdaten aus Kalibration', numbering = False)):
            with doc.create(LongTable("|c|c|c|")) as data_table:
                data_table.add_hline()
                data_table.add_row(["Pressure [bar]","øDigit","std Digit"])
                data_table.add_hline()
                for n in range(0,len(self.Referencedata.mw)):
                    data_table.add_row([round(self.Referencedata.mw[n],3),round(self.Sensordata.mw[n]*65535,2),round(self.Sensordata.std[n],2)])
                    data_table.add_hline()
        doc.generate_pdf('Kalibration-' + self.sensorname, clean_tex=True)
    

    def run(self):
        self.sensordaten_einlesen()
        self.referenzdaten_einlesen()
        self.referenz_verarbeiten(True)
        self.sensorverarbeiten()
        self.fitsensor()
        self.report()
        
class Channel():
    """Verarbeitet Rohdaten eines Thermokanals von einer Kalibrierung mit Wieland Geräten"""
    def __init__(self):
        self.mw = []
        self.std = []
        self.best = []
        self.covar = []
        
    def calc_cubic(self,mw,A0,A1,A2,A3):
        """Berechnet kalibrierte werte von mw nach kubischen Fit""" 
        return (A0 + A1 * mw + A2 * mw**2 + A3 * mw**3)        
        
    def calc_quad(self,mw,A0,A1,A2):
        """Berechnet kalibrierte werte von mw nach quadratischem Fit""" 
        return (A0 + A1 * mw + A2 * mw**2)
    
    def calc_lin(self,mw,A0,A1):
        """Berechnet kalibrierte werte von mw nach linearem Fit"""
        return (A0 + A1 * mw)
      
    def justmw(self, master):
        """Mittelwertbildung"""

        for n in range(len(master.caldata)//master.referenceblock):
            self.mw.append(np.mean(master.caldata[n*master.referenceblock:(n+1)*master.referenceblock-1])/65535)
            self.std.append(np.std(master.caldata[n*master.referenceblock:(n+1)*master.referenceblock-1]))
        self.mw = np.asarray(self.mw)
        self.std = np.asarray(self.std)        
        
    def calibrate(self, master):
        """Kalibriert verschiedene Sensortypen(Druck) auf Referenzdruck"""
        if master.polyorder == 'linear':
            self.fitfunction = "A0 + A1 * D"
            self.fit_fkt = self.calc_lin
        elif master.polyorder == 'quadratic':
            self.fit_fkt = self.calc_quad
            self.fitfunction = "A0 + A1 * D + A2 * D**2"
        elif master.polyorder == "cubic":
            self.fitfunction = "A0 + A1 * D + A2 * D**2 + A3 * D**3"
            self.fit_fkt = self.calc_cubic
        else:
            print("Polynomgrad nicht definiert")
            
        self.mw = np.asarray(self.mw)
        if master.sensortype == "Druck":
            self.best, self.covar = curve_fit(self.fit_fkt, self.mw, master.Referencedata.caldat)
        else:
            print("Sensortyp noch nicht Hinterlegt")
                
    def rsme(self,master):
        if master.sensortype == "Druck":
            ss_res = np.dot((master.Referencedata.caldat - master.Sensordata.fit_fkt(master.Sensordata.mw, *master.Sensordata.best))
                            ,(master.Referencedata.caldat - master.Sensordata.fit_fkt(master.Sensordata.mw, *master.Sensordata.best)))
            ymean = np.mean(master.Referencedata.caldat)
            ss_tot = np.dot((master.Referencedata.caldat-ymean),(master.Referencedata.caldat-ymean))
            master.rsme = 1-ss_res/ss_tot
        else:
            print("Sensortyp noch nicht Hinterlegt")
    

class Reference():
    """Mittelung und Standardabweichung von Daten für Referenzdruck"""
    def __init__(self):
        self.mw = []
        self.std = []
        self.caldat = []
        
    def mittelwerte(self, master):
        """Mittelwertbildung"""
        for n in range(len(master.refdata)//master.referenceblock):
            self.mw.append(np.mean(master.refdata[n*master.referenceblock:(n+1)*master.referenceblock-1]))
            self.std.append(np.std(master.refdata[n*master.referenceblock:(n+1)*master.referenceblock-1]))
        self.mw = np.asarray(self.mw)
        self.std = np.asarray(self.std)
        
    def calibrate(self, master):
        """Kalibriert Mittelwerte von Druckmodul"""
        if master.referencetype == "Block":
            self.caldat = self.mw        
        else:
            print("Kein gültiger Referenzsensortyp")   
            
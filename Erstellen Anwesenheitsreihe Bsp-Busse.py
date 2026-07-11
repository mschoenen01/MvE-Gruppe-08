#%% Bibliotheken importieren

import pypsa
import pandas as pd
import numpy as np
import csv

#%% df Import

df = pd.read_csv("Fahrzeiten 3 Busse Bsp neu.CSV", sep=";", dtype=int)

bus1_abfahrt = df.iloc[0, 0]
bus1_ankommen = df.iloc[0, 1]
bus2_abfahrt = df.iloc[0, 2]
bus2_ankommen = df.iloc[0, 3]
bus3_abfahrt = df.iloc[0, 4]
bus3_ankommen = df.iloc[0, 5]

print(bus2_abfahrt)

#%% In Datenformat umwandeln



#%% Schleife

with open("Fahrzeiten 3 Busse Bsp.CSV", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow(["Snapshot", "Ladeleistung Bus1", "Ladeleistung Bus2", "Ladeleistung Bus3"])

    for i in range(96):

        ladezustand_bus1 = 0 if i >= bus1_abfahrt and i < bus1_ankommen else 1

        ladezustand_bus2 = 0 if i >= bus2_abfahrt and i < bus2_ankommen else 1

        ladezustand_bus3 = 0 if i >= bus3_abfahrt and i < bus3_ankommen else 1

        writer.writerow([i, ladezustand_bus1, ladezustand_bus2, ladezustand_bus3])



#Erstelle csv-Datei mit 0 oder 1 für Bus1 für jede Viertelstunde eines Tages
# %%

'''
 i = 0

    while i < 96:

        if i < bus1_abfahrt:
            ladezustand_bus1 = 1
        elif i >= bus1_abfahrt and i < bus1_ankommen:
            ladezustand_bus1 = 0
        elif i >= bus1_ankommen:
            ladezustand_bus1 = 1
        else:
            print("fehler")

        print(ladezustand_bus1)
'''
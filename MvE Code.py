#%% 
#++++++++++ Bibliotheken importieren ++++++++++

import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#%%

#++++++++++ Datenimport ++++++++++

df_spotmarktpreis = pd.read_csv("Strompreis dynamisch interpoliert.csv", sep=';', decimal=',')
einstrahlung_süd = pd.read_csv("pv_süd_interpoliert.csv", sep=',', decimal='.')
einstrahlung_west = pd.read_csv("pv_west_interpoliert.csv", sep=',', decimal='.')
einstrahlung_ost = pd.read_csv("pv_ost_interpoliert.csv", sep=',', decimal='.')

lastprofil_standort = pd.read_csv("G25_Gewerbeprofil_2024_500000kWh_15min.csv", sep=';', decimal=',')

lastprofil_ebus = pd.read_csv("PyPSA_Bus_Verbrauch_15min_Jahr-v2.csv", sep=',', decimal='.') #ohne Feiertage!! mit KI auf Basis eines realer Umlaufplans erstellt, stichprobenartig validiert
lastprofil_ebus *= 4 #das Profil wurde bereits geviertelt, aber wegen snapshot_weightings muss es wieder mit 4 multipliziert werden, da es durch die Funktion geviertelt wird
anwesenheit_ebus = pd.read_csv("Bus_Anwesenheit_15min_Woche-v2.csv", sep=',') #mit KI auf Basis eines realer Umlaufplans erstellt, stichprobenartig validiert

#%% 

#++++++++++ Parameter +++++++++

#Annuität
#Annahme: Verkehrsvertrag dauert nur 10 Jahre an; Setup muss sich bis dahin refinanziert haben. 
#Weitere Annahme, dass alle betrachteten Komponenten eine Mindestlebensdauer von 10 Jahre haben oder bei Schaden unter Garantie fallen.
p = 0.02 #Zinssatz
q = 1.02 #1+Zinssatz
laufzeit = 10 #a

#Netz
dynamischer_strompreis = df_spotmarktpreis["Strompreis dyn. 2030 ME"]
strompreis_statisch = dynamischer_strompreis.mean() # €/kWh
einspeisevergütung = -0.07 #€/kWh #Annahme: Mittelwert von Direktvermarktung/PPA

#PV
capex_pv = 639 # €/kWp
capex_pv_anuity = capex_pv * ((p * q**laufzeit) / (q**laufzeit - 1))
opex_pv = 0.01*capex_pv_anuity # 1% der Investitionskosten pro Jahr
#Carport
capex_pv_carport = 2000 # €/kWp
capex_pv_carport_anuity = capex_pv_carport * ((p * q**laufzeit) / (q**laufzeit - 1))
opex_pv_carport = 0.01*capex_pv_carport_anuity # 1% der Investitionskosten pro Jahr

#E-Busse
e_nom_ebus = 580 # kWh  #Annahme: liegt knapp überhalb der minimal benötigten Energie, um die Simulation nicht zu limitieren
effizienz_ebus_laden = 0.99
effizienz_ebus_entladen = 0.99
#opex_ebus = unterhaltungskosten personalkosten #Annahme: vernachlässigbar, da es bereits vorhandene Infrastruktur und Kosten sind
#unterhaltungskosten = 0.40 #€/km 
#personalkosten = 901000 #€/a
#selbstentladung_ebus =  #Annahme: vernachlässigbar, da minimal 
#degradation    #Annahme: vernachlässigbar, da Einfluss auf Simulation nur größere Buskapazität bedeuten würde, die wir nicht verändern wollen
min_soc_bs = 0.1
max_soc_bs = 0.9

#Batteriespeicher stationär
effizienz_bs_laden = 0.89
effizienz_bs_entladen = 0.89
degradation_bs = 0.8 #nach 10 Jahren 80 % Batteriekapazität vorhanden 
capex_bs = 300/degradation_bs # €/kWh Quelle: https://www.wireload.de/shop/Batteriespeicher-Containerlosung-1MWh-Speicherkapazitat-1kW-Leistung-p820225379
capex_bs_anuity = capex_bs * ((p * q**laufzeit) / (q**laufzeit - 1))
opex_bs = 0.05 * capex_bs_anuity #€/kWh*a     #Quelle?????????? 
#selbstentladung_bs  #Annahme: vernachlässigbar, da minimal
#min_soc_bs = 0.1 
#max_soc_bs = 0.9 

#Ladesäule
effizienz_ladesäule_laden = 0.88
effizienz_ladesäule_entladen = 0.6
p_nom_ladesäule = 300 #kW  #Quelle???????
#opex_ladesäule = 3000 #€/a
#capex_ladesäule = 10000 #€/a


#Vergleich: stationärer Speicher, dyn Tarife, bidirek. Laden, PV#


# %%

#++++++++++ Network erstellen++++++++++

network = pypsa.Network()

#++++++++++ Snapshots +++++++++ 

network.set_snapshots(range(4*8760))
network.snapshot_weightings[:] = 0.25

#++++++++++ Bus +++++++++

network.add("Bus", name = "Electricity")
network.add("Bus", name = "BS")


#++++++++++ Generatoren ++++++++++

network.add("Generator", name = "Stromnetz", bus = "Electricity", p_nom = 10000, marginal_cost = dynamischer_strompreis)
network.add("Generator", name = "PV", bus = "Electricity", p_nom_extendable = True, p_nom_max = 290, p_max_pu = einstrahlung_süd["PV Leistung in kW"].values, capital_cost = capex_pv_anuity, marginal_cost = opex_pv)
network.add("Generator", name = "Einspeisung", bus = "Electricity", p_nom = 10000, sign = -1, marginal_cost = einspeisevergütung)
network.add("Generator", name = "PV Carport Ost", bus = "Electricity", p_nom_extendable = True, p_max_pu = einstrahlung_ost["PV Leistung in kW"].values, capital_cost = capex_pv_carport_anuity, marginal_cost = opex_pv_carport)
network.add("Generator", name = "PV Carport West", bus = "Electricity", p_nom_extendable = True, p_max_pu = einstrahlung_west["PV Leistung in kW"].values, capital_cost = capex_pv_carport_anuity, marginal_cost = opex_pv_carport)

#++++++++++ Storages +++++++++++

network.add("Store", name = "BS stationär", bus = "BS", e_nom_extendable = True, e_nom_max = 10000, capital_cost = capex_bs_anuity, marginal_cost = opex_bs) 

#++++++++++ Loads ++++++++++

network.add("Load", name = "Last_Standort", bus = "Electricity", p_set = lastprofil_standort["Last_kWh"].values) 

#*********** Links ++++++++++

network.add("Link", name="bs_charge", bus0="Electricity", bus1="BS", efficiency=effizienz_bs_laden, p_nom = 250)
network.add("Link", name="bs_discharge", bus0="BS", bus1="Electricity", efficiency=effizienz_bs_entladen, p_nom = 250)



# %%
#E-Busse Schleife
anzahl_ebusse = 19

for i in range(1, anzahl_ebusse+1):
    bus_node = f"E-Bus_{i}"
    
    network.add("Bus", name=bus_node)
    
    #Laden
    network.add("Link", 
                name=f"charge_ladesäule_{i}", 
                bus0="Electricity", 
                bus1=bus_node, 
                p_nom=p_nom_ladesäule,
                #p_nom_extendable=True,
                efficiency=effizienz_ladesäule_laden,
                p_max_pu=anwesenheit_ebus[f"Bus_{i}"]
                )
                
    # Entladen
    network.add("Link", 
                name=f"discharge_ladesäule_{i}", 
                bus0=bus_node, 
                bus1="Electricity",
                p_nom=p_nom_ladesäule,
                #p_nom_extendable=True,
                efficiency=effizienz_ladesäule_entladen,
                p_max_pu=anwesenheit_ebus[f"Bus_{i}"]
                )
    
    #Last
    network.add("Load", 
                name=f"Load_{i}", 
                bus=bus_node, 
                p_set= (1-(anwesenheit_ebus[f"Bus_{i}"])) * lastprofil_ebus[f"Bus_{i}"] 
                ) 
    
    #E-Bus-Batterie als Speicher
    network.add("Store", 
                name=f"E-Bus_{i}_store", 
                bus=bus_node,
                #e_nom_extendable=True, 
                #e_nom_mod = 50, #kWh #Schrittweite auf 50 kWh, um Simulationszeit zu begrenzen
                e_nom = e_nom_ebus, #kWh 
                #capital_cost = 1000, 
                e_min_pu = min_soc_bs,
                e_max_pu = max_soc_bs           
                )

# Check, ob Generierung mit Schleife erfolgreich war:
print(network.stores.index.tolist())
print(network.links.index.tolist())
print(network.buses.index.tolist())
print(network.loads.index.tolist())


# %%

#++++++++++ Abfahrt!!! ++++++++++

network.optimize(solver_name="highs") #warum highs???

# %%
#++++++Auswerten der Ergebnisse+++++++

#%% Kosten

#Stromkosten

stromverbrauch_jährlich = network.generators_t.p["Stromnetz"]
strompreis_jährlich = network.generators_t.marginal_cost["Stromnetz"]
einspeisung_jährlich = network.generators_t.p["Einspeisung"]

stromkosten_jährlich = (stromverbrauch_jährlich * strompreis_jährlich * network.snapshot_weightings.objective).sum() - (einspeisung_jährlich * einspeisevergütung * network.snapshot_weightings.objective).sum()

#OPEX PV

opex_pv_carport_ost_kosten_jährlich = opex_pv_carport * network.generators.p_nom_opt["PV Carport Ost"]
opex_pv_carport_west_kosten_jährlich = opex_pv_carport * network.generators.p_nom_opt["PV Carport West"]

opex_pv_kosten_jährlich = opex_pv * network.generators.p_nom_opt["PV"]

#CAPEX PV

capex_pv_kosten_jährlich = capex_pv_anuity * network.generators.p_nom_opt["PV"]

capex_pv_carport_ost_kosten_jährlich = capex_pv_carport_anuity * network.generators.p_nom_opt["PV Carport Ost"]
capex_pv_carport_west_kosten_jährlich = capex_pv_carport_anuity * network.generators.p_nom_opt["PV Carport West"]

#OPEX BS stationär

opex_bs_kosten_jährlich = opex_bs * network.stores.e_nom_opt["BS stationär"]

#CAPEX BS stationär

capex_bs_kosten_jährlich = capex_bs_anuity * network.stores.e_nom_opt["BS stationär"]

#Gesamtkosten

gesamtkosten_jährlich = (
    stromkosten_jährlich
    + opex_pv_kosten_jährlich
    + capex_pv_carport_ost_kosten_jährlich
    + capex_pv_carport_west_kosten_jährlich
    + opex_bs_kosten_jährlich
    + capex_bs_kosten_jährlich
)

gesamtkosten_10_jahre = gesamtkosten_jährlich * 10

print(f"Die jährlichen Gesamtkosten betragen: {round(gesamtkosten_jährlich, 2)} €")
print(f"Die Kosten über die Betriebsdauer von 10 Jahren betragen: {round(gesamtkosten_10_jahre, 2)} €")

# %%

#++++++ Ausgeben der Ergebnisse/Plots +++++++

#Szenario 1: Basis (nur Netzbezug; ohne PV, ohne BS, ohne bidir. Laden)

#Szenario 2: Maximale Wirtschaftlichkeit (PV und BS extendable ohne Begrenzung; mit bidir. Laden)

#Szenario 3: Maximale Umsetzbarkeit (PV und BS extendable, aber begrenzt; mit bidir. Laden)

# %%
network.stores

# %%
#network.links_t.p0["charge_ladesäule_2"][0:672].plot()
#network.generators_t.p["PV"][20162:20834].plot()
network.stores_t.e["BS stationär"][20162:20834].plot()
#network.loads_t.p["Last_Standort"][20162:20834].plot()
#network.links_t.p_max_pu[20162:20834].plot()

network.links_t.p_max_pu["charge_ladesäule_5"]

# %%

#%%
network.links_t.p0["discharge_ladesäule_1"][0:700].plot()
network.links_t.p0["discharge_ladesäule_2"][0:700].plot()
network.links_t.p0["discharge_ladesäule_3"][0:700].plot()
network.links_t.p0["discharge_ladesäule_4"][0:700].plot()
network.links_t.p0["discharge_ladesäule_5"][0:700].plot()
network.links_t.p0["discharge_ladesäule_6"][0:700].plot()
network.links_t.p0["discharge_ladesäule_7"][0:700].plot()
network.links_t.p0["discharge_ladesäule_8"][0:700].plot()
network.links_t.p0["discharge_ladesäule_9"][0:700].plot()
network.links_t.p0["discharge_ladesäule_10"][0:700].plot()
network.links_t.p0["discharge_ladesäule_11"][0:700].plot()
network.links_t.p0["discharge_ladesäule_12"][0:700].plot()
network.links_t.p0["discharge_ladesäule_13"][0:700].plot()
network.links_t.p0["discharge_ladesäule_14"][0:700].plot()
network.links_t.p0["discharge_ladesäule_15"][0:700].plot()
network.links_t.p0["discharge_ladesäule_16"][0:700].plot()
network.links_t.p0["discharge_ladesäule_17"][0:700].plot()
network.links_t.p0["discharge_ladesäule_18"][0:700].plot()
network.links_t.p0["discharge_ladesäule_19"][0:700].plot()

#%%
network.stores_t.e["E-Bus_11_store"][0:700].plot()
network.stores_t.e["E-Bus_12_store"][0:700].plot()

# %%

network.generators_t.p["Einspeisung"][0:700].plot()
# %%
network.generators
# %%

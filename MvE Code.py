#%% 

#++++++++++ Bibliotheken importieren ++++++++++

import pypsa
import pandas as pd
import numpy as np

#%%

#++++++++++ Datenimport ++++++++++

df_spotmarktpreis = pd.read_csv("Strompreis dynamisch interpoliert.csv", sep=';', decimal=',')
einstrahlung_süd = pd.read_csv("pv_süd_interpoliert.csv", sep=',', decimal='.')
einstrahlung_west = pd.read_csv("pv_west_interpoliert.csv", sep=',', decimal='.')
einstrahlung_ost = pd.read_csv("pv_ost_interpoliert.csv", sep=',', decimal='.')

lastprofil_standort = 5 #!!!!!!!!!!!!!!! Moritz
lastprofil_ebus = 5.70 #kW 

anwesenheit_ebus = pd.read_csv("Bus_Anwesenheit_15min_Woche-v2.csv", sep=',')

#print(anwesenheit_ebus)


#%% 

#++++++++++ Parameter +++++++++

#Netz
dynamischer_strompreis = df_spotmarktpreis["Strompreis dyn. 2030 ME"]
strompreis_statisch = dynamischer_strompreis.mean() # €/kWh
einspeisevergütung = -0.07 #€/kWh ???????????? Jonathan

#PV
capex_pv = 639 # €/kWp
opex_pv = 0.01 # 1% der Investitionskosten pro Jahr

#E-Busse
e_nom_ebus = 1000 # kWh ?????????????
effizienz_ebus_laden = 0.99
effizienz_ebus_entladen = 0.99
#opex_ebus = 0#????????? Marius 
#selbstentladung_ebus = 0 #???????

#Batteriespeicher stationär
capex_bs = 500 # €/kWh ??????? Marie Kosten in Präsi
#opex_bs=0 # €/kWh ??????????
effizienz_bs_laden = 0.89
effizienz_bs_entladen = 0.89
#selbstentladung_bs=  #?????? Marius 
#min_soc_bs = 0.1 ??????? Marius
#max_soc_bs = 0.9 ??????? Marius

#Ladesäule
#opex_ladesäule=0 #€/kWh ?????????????
effizienz_ladesäule_laden=0.88
effizienz_ladesäule_entladen=0.6
p_nom_ladesäule= 300 #kW Annahme durch Quelle ersetzen, Jonathan ????????????
opex_ladesäule = 3000 #€/a

#%%

print(len(einstrahlung_süd))
print(len(einstrahlung_west))
print(len(einstrahlung_ost))
print(len(dynamischer_strompreis))
print(len(anwesenheit_ebus))
# %%

#++++++++++ Network erstellen++++++++++

network = pypsa.Network()

#++++++++++ Snapshots +++++++++ 

network.set_snapshots(range(4*8760))

#++++++++++ Bus +++++++++

network.add("Bus", name = "Electricity")
#network.add("Bus", name = "E-Bus")
#network.add("Bus", name = "BS")

#++++++++++ Generatoren ++++++++++

network.add("Generator", name = "Stromnetz", bus = "Electricity", p_nom = 10000, marginal_cost = dynamischer_strompreis)
network.add("Generator", name = "PV", bus = "Electricity", p_nom_extendable = True, p_max_pu = einstrahlung_süd["PV Leistung in kW"].values, capital_cost = capex_pv)
network.add("Generator", name = "Einspeisung", bus = "Electricity", p_nom = 10000, sign = -1, marginal_cost = einspeisevergütung)

#++++++++++ Storages +++++++++++

network.add("Store", name = "BS stationär", bus = "Electricity", e_nom_extendable = True, e_nom_max = 10000, capital_cost = capex_bs)

#network.add("Store", name = "E-Bus 1", bus = "E-Bus", e_nom = e_nom_ebus)   #Kosten weglassen? (Die Entscheidung wurde ja quasi getroffen,
                                                                            #dass solche E-Busse vorhanden sein sollen, daher ggf. Kosten nicht relevant)

#++++++++++ Loads ++++++++++

network.add("Load", name = "Last_Standort", bus = "Electricity", p_set = lastprofil_standort)
#network.add("Load", name = "Last E-Bus", bus = "Electricity", p_set = lastprofil_ebus)

#++++++++++ Links ++++++++++

#network.add("Link", name = "E-Bus laden", bus0 = "Electricity", bus1 = "E-Bus", p_nom_max = 10000, efficiency = effizienz_ebus_laden)
#network.add("Link", name = "E-Bus entladen", bus0 = "E-Bus", bus1 = "Electricity", p_nom_max = 10000, efficiency = effizienz_ebus_entladen)
#network.add("Link", name = "BS laden", bus0 = "E-Bus", bus1 = "Electricity", p_nom_max = 10000, efficiency = effizienz_ebus_entladen)

# %%
#E-Busse Schleife
anzahl_ebusse = 19

for i in range(1, anzahl_ebusse + 1):
    bus_node = f"E-Bus_{i}"
    
    network.add("Bus", name=bus_node)
    
    #Laden
    network.add("Link", 
                name=f"charge_ladesäule_{i}", 
                bus0="Electricity", 
                bus1=bus_node, 
                #p_nom_extendable=True,
                p_nom=p_nom_ladesäule,
                efficiency=effizienz_ladesäule_laden,
                p_max_pu=anwesenheit_ebus[f"Bus_{i}"],
                marginal_cost = opex_ladesäule / 2
                )
    
    # Entladen
    # WICHTIG: Die marginal_cost verhindern exzessives Arbitrage-Trading und schonen die Batterie.
    network.add("Link", 
                name=f"discharge_ladesäule_{i}", 
                bus0=bus_node, 
                bus1="Electricity", 
                #p_nom_extendable= True,
                p_nom=p_nom_ladesäule,
                efficiency=effizienz_ladesäule_entladen,
                p_max_pu=anwesenheit_ebus[f"Bus_{i}"],
                marginal_cost = opex_ladesäule / 2
                 )
    
    #Last
    network.add("Load", 
                name=f"Load_{i}", 
                bus=bus_node, 
                p_set= (1-(anwesenheit_ebus[f"Bus_{i}"])) * lastprofil_ebus
                ) 
    
    #E-Bus-Batterie als Speicher
    network.add("Store", 
                name=f"E-Bus_{i}_store", 
                bus=bus_node,
                #e_nom_extendable=True, 
                e_nom = e_nom_ebus, #kWh  
                #e_nom_extendable=True,
                #capital_cost=1, #€/kWh                
                e_cyclic=True #sinnvoll? 
                )

# Check, ob Generierung erfolgreich war:
print(network.stores.index.tolist())
print(network.links.index.tolist())
print(network.buses.index.tolist())
print(network.loads.index.tolist())


#%%
#network.links_t.p_max_pu["charge_ladesäule_5"]
#%%

#++++++++++ Visualisierung ++++++++++

print("Durchschnittlicher Strompreis in 2030 beträgt",round(strompreis_statisch, 2), "ct/kWh")

# %%

#++++++++++ Abfahrt!!! ++++++++++

network.optimize(solver_name="highs")
# %%
network.generators
# %%
network.stores

# %%
#network.links_t.p0["charge_ladesäule_2"][0:672].plot()
#network.generators_t.p["PV"][20162:20834].plot()
#network.stores_t.e["BS stationär"][20162:20834].plot()
#network.loads_t.p["Last_Standort"][20162:20834].plot()
#network.links_t.p_max_pu[20162:20834].plot()

# %%
network.links_t.p0["charge_ladesäule_6"][20462:20634].plot()
network.links_t.p0["discharge_ladesäule_6"][20462:20634].plot()
network.stores_t.e["E-Bus_6_store"][20462:20634].plot()

# %%

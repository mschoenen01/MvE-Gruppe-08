#%% 

#++++++++++ Bibliotheken importieren ++++++++++

import pypsa
import pandas as pd
import numpy as np

#%%

#++++++++++ Datenimport ++++++++++

df_spotmarktpreis = pd.read_csv("Strompreis dynamisch interpoliert.csv", sep=';', decimal=',')
dynamischer_strompreis = df_spotmarktpreis["Strompreis dyn. 2030 ME"]
einstrahlung_süd = pd.read_csv("pv_süd_interpoliert.csv", sep=',', decimal='.')
einstrahlung_west = pd.read_csv("pv_west_interpoliert.csv", sep=',', decimal='.')
einstrahlung_ost = pd.read_csv("pv_ost_interpoliert.csv", sep=',', decimal='.')

lastprofil_standort = 5 #!!!!!!!!!!!!!!!
lastprofil_ebus = 10 #!!!!!!!!!!!!!

# %% 

#++++++++++ Plots +++++++++++

dynamischer_strompreis[100:220].plot()

#%%
einstrahlung_süd["PV Leistung in kW"].plot()
einstrahlung_west["PV Leistung in kW"].plot()
einstrahlung_ost["PV Leistung in kW"].plot()
#%% 

#++++++++++ Parameter +++++++++

cost_bs = 500 # Marie Kosten in Präsi €/kWh
capex_pv = 639 # €/kWp
opex_pv = 0.01 # 1% der Investitionskosten pro Jahr
strompreis_statisch = dynamischer_strompreis.mean() # €/kWh
einspeisevergütung = -0.07 #€/kWh ????????????
e_nom_ebus = 200 # kWh ?????????????
effizienz_ebus_laden = 0.99
effizienz_ebus_entladen = 0.99
effizienz_bs_laden = 0.99
effizienz_bs_entladen = 0.99


# %%

#++++++++++ Network erstellen++++++++++

network = pypsa.Network()

#++++++++++ Snapshots +++++++++ 

network.set_snapshots(range(8760*4))

#++++++++++ Bus +++++++++

network.add("Bus", name = "Electricity")
network.add("Bus", name = "E-Bus")
#network.add("Bus", name = "BS")

#++++++++++ Generatoren ++++++++++

network.add("Generator", name = "Stromnetz", bus = "Electricity", p_nom = 10000, marginal_cost = dynamischer_strompreis)
network.add("Generator", name = "PV", bus = "Electricity", p_nom_extendable = True, p_max_pu = einstrahlung_süd["PV Leistung in kW"], capital_cost = capex_pv)
network.add("Generator", name = "Einspeisung", bus = "Electricity", p_nom = 10000, sign = -1, marginal_cost = einspeisevergütung)

#++++++++++ Storages +++++++++++

network.add("Store", name = "BS stationär", bus = "Electricity", e_nom_extendable = True, e_nom_max = 10000, capital_cost = cost_bs)

network.add("Store", name = "E-Bus 1", bus = "E-Bus", e_nom = e_nom_ebus)   #Kosten weglassen? (Die Entscheidung wurde ja quasi getroffen,
                                                                            #dass solche E-Busse vorhanden sein sollen, daher ggf. Kosten nicht relevant)

#++++++++++ Loads ++++++++++

network.add("Load", name = "Last Standort", bus = "Electricity", p_set = lastprofil_standort)
network.add("Load", name = "Last E-Bus", bus = "Electricity", p_set = lastprofil_ebus)

#++++++++++ Links ++++++++++

network.add("Link", name = "E-Bus laden", bus0 = "Electricity", bus1 = "E-Bus", p_nom_max = 10000, efficiency = effizienz_ebus_laden)
network.add("Link", name = "E-Bus entladen", bus0 = "E-Bus", bus1 = "Electricity", p_nom_max = 10000, efficiency = effizienz_ebus_entladen)
#network.add("Link", name = "BS laden", bus0 = "E-Bus", bus1 = "Electricity", p_nom_max = 10000, efficiency = effizienz_ebus_entladen)

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

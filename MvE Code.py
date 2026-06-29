#%% Bibliotheken importieren

import pypsa
import pandas as pd
import numpy as np

#%% Datenimport

dynamischer_strompreis = pd.read_csv("Strompreis.csv", sep=';', decimal=',')
einstrahlung_süd = pd.read_csv("Süd_1kWp_30Neigung_0Azimuth.csv", sep=';', decimal=',')
einstrahlung_west = pd.read_csv("West_1kWp_15Neigung_90Azimuth.csv", sep=';', decimal=',')
einstrahlung_ost = pd.read_csv("Ost_1kWp_15Neigung_-90Azimuth.csv", sep=';', decimal=',')
# %% Plots

dynamischer_strompreis["Strompreis dyn. 2030 ME"].plot()
einstrahlung_süd.plot()
einstrahlung_west.plot()
einstrahlung_ost.plot()
#%% Parameter

cost_bs = 500 # Marie Kosten in Präsi €/kWh
cost_pv = 500 # Marius PV Kosten in Präsi €/kWp
strompreis_dynamisch = dynamischer_strompreis["Strompreis dyn. 2030 ME"]
strompreis_statisch = strompreis_dynamisch.mean() # €/kWh

# %% Network erstellen

network = pypsa.Network()
network.set_snapshots(range(8760))

# Snapshots

network.add("Bus", name = "E-Bus")

network.add("Generator", name = "Stromnetz", bus = "E-Bus", p_nom = 100, marginal_cost = strompreis_dynamisch)
network.add("Generator", name = "PV", bus = "E-Bus", p_nom_extendable = True)


#%%

print("Durchschnittlicher Strompreis in 2030 beträgt",round(strompreis_statisch, 2), "ct/kWh")

# %%

network.optimize(solver_name="highs")
# %%
network.generators
# %%

#asdf
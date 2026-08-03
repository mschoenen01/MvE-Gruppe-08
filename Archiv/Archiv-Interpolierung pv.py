#%%
import numpy as np
import pandas as pd

#%%

pv_ost = pd.read_csv("Ost_1kWp_15Neigung_-90Azimuth.csv", sep=",", decimal=".", index_col=0)
pv_süd =pd.read_csv("Süd_1kWp_30Neigung_0Azimuth.csv", sep=",", decimal=".", index_col=0)
pv_west = pd.read_csv("West_1kWp_15Neigung_90Azimuth.csv", sep=",", decimal=".", index_col=0)

#%% Ost

for i in range(len(pv_ost)):

    if i % 4 != 0:
        pv_ost.loc[i, "PV Leistung in kW"] = np.nan
    
pv_ost["PV Leistung in kW"] = pv_ost["PV Leistung in kW"].interpolate(method="linear")
pv_ost.to_csv("pv_ost_interpoliert.csv")
# %% Süd

for i in range(len(pv_süd)):

    if i % 4 != 0:
        pv_süd.loc[i, "PV Leistung in kW"] = np.nan
    
pv_süd["PV Leistung in kW"] = pv_süd["PV Leistung in kW"].interpolate(method="linear")
pv_süd.to_csv("pv_süd_interpoliert.csv")
# %% West

for i in range(len(pv_west)):

    if i % 4 != 0:
        pv_west.loc[i, "PV Leistung in kW"] = np.nan
    
pv_west["PV Leistung in kW"] = pv_west["PV Leistung in kW"].interpolate(method="linear")
pv_west.to_csv("pv_west_interpoliert.csv")
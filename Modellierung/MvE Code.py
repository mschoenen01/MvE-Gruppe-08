#%% Bibliotheken importieren

import pypsa
import pandas as pd
import numpy as np

#%% Datenimport

dynamischer_strompreis = pd.read_csv("Strompreis.csv", sep=';', decimal=',')
# %%
dynamischer_strompreis["Strompreis dyn. 2040 SE"].plot()
# %%# Test

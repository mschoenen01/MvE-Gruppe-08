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
dynamischer_strompreis = df_spotmarktpreis["Strompreis dyn. 2030 ME"]/100 # damit €/kWh vorliegen
strompreis_statisch = dynamischer_strompreis.mean() # €/kWh
einspeisevergütung = -0.07 #€/kWh #Annahme: Mittelwert von Direktvermarktung/PPA

#PV
capex_pv = 639 # €/kWp
capex_pv_anuity = capex_pv * ((p * q**laufzeit) / (q**laufzeit - 1))
opex_pv = 0.01*capex_pv_anuity # 1% der Investitionskosten pro Jahr
fixkosten_pv_jährlich = capex_pv_anuity + opex_pv
#Carport
capex_pv_carport = 2000 # €/kWp
capex_pv_carport_anuity = capex_pv_carport * ((p * q**laufzeit) / (q**laufzeit - 1))
opex_pv_carport = 0.01*capex_pv_carport_anuity # 1% der Investitionskosten pro Jahr
fixkosten_pv_carport_jährlich = capex_pv_carport_anuity + opex_pv_carport

#E-Busse
e_nom_ebus = 570 # kWh  #Annahme: liegt knapp überhalb der minimal benötigten Energie, um die Simulation nicht zu limitieren
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
fixkosten_bs = capex_bs_anuity + opex_bs
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

#%%
dynamischer_strompreis[16922:17000].plot()
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
network.add("Generator", name = "PV", bus = "Electricity", p_nom_extendable = True, p_nom_max = 290, p_max_pu = einstrahlung_süd["PV Leistung in kW"].values, capital_cost = fixkosten_pv_jährlich)
network.add("Generator", name = "Einspeisung", bus = "Electricity", p_nom = 10000, sign = -1, marginal_cost = einspeisevergütung)
network.add("Generator", name = "PV Carport West", bus = "Electricity", p_nom_extendable = True, p_nom_max = 5000, p_max_pu = einstrahlung_west["PV Leistung in kW"].values, capital_cost = fixkosten_pv_carport_jährlich)
network.add("Generator", name = "PV Carport Ost", bus = "Electricity", p_nom_extendable = True, p_nom_max = 5000, p_max_pu = einstrahlung_ost["PV Leistung in kW"].values, capital_cost = fixkosten_pv_carport_jährlich)
network.add("Generator", name = "PV Carport Süd", bus = "Electricity", p_nom_extendable = True, p_nom_max = 5000, p_max_pu = einstrahlung_süd["PV Leistung in kW"].values, capital_cost = fixkosten_pv_carport_jährlich)

#++++++++++ Storages +++++++++++

network.add("Store", name = "BS stationär", bus = "BS", e_nom_extendable = True, e_nom_max = 1000, capital_cost = fixkosten_bs) 

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
                #e_nom_max = 580,
                #capital_cost = 10000, 
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

network.optimize(solver_name="gurobi")

# %%
#++++++Auswerten der Ergebnisse+++++++

#%% Kosten

#Stromkosten

stromverbrauch_jährlich = network.generators_t.p["Stromnetz"]
strompreis_jährlich = network.generators_t.marginal_cost["Stromnetz"] # bei dynamischem Tarif mit network.generators_t...; bei statischem Tarif ohne_t
einspeisung_jährlich = network.generators_t.p["Einspeisung"]

stromkosten_jährlich = (stromverbrauch_jährlich * strompreis_jährlich * network.snapshot_weightings.objective).sum() + (einspeisung_jährlich * einspeisevergütung * network.snapshot_weightings.objective).sum()

#OPEX PV

opex_pv_carport_ost_kosten_jährlich = opex_pv_carport * network.generators.p_nom_opt["PV Carport Ost"]
opex_pv_carport_west_kosten_jährlich = opex_pv_carport * network.generators.p_nom_opt["PV Carport West"]
opex_pv_carport_süd_kosten_jährlich = opex_pv_carport * network.generators.p_nom_opt["PV Carport Süd"]

opex_pv_kosten_jährlich = opex_pv * network.generators.p_nom_opt["PV"]

#CAPEX PV

capex_pv_kosten_jährlich = capex_pv_anuity * network.generators.p_nom_opt["PV"]

capex_pv_carport_ost_kosten_jährlich = capex_pv_carport_anuity * network.generators.p_nom_opt["PV Carport Ost"]
capex_pv_carport_west_kosten_jährlich = capex_pv_carport_anuity * network.generators.p_nom_opt["PV Carport West"]
capex_pv_carport_süd_kosten_jährlich = capex_pv_carport_anuity * network.generators.p_nom_opt["PV Carport Süd"]

#OPEX BS stationär

opex_bs_kosten_jährlich = opex_bs * network.stores.e_nom_opt["BS stationär"]

#CAPEX BS stationär

capex_bs_kosten_jährlich = capex_bs_anuity * network.stores.e_nom_opt["BS stationär"]

#Gesamtkosten

gesamtkosten_jährlich = (
    stromkosten_jährlich
    + capex_pv_kosten_jährlich
    + opex_pv_kosten_jährlich
    + capex_pv_carport_ost_kosten_jährlich
    + opex_pv_carport_ost_kosten_jährlich
    + opex_pv_carport_west_kosten_jährlich
    + capex_pv_carport_west_kosten_jährlich
    + opex_pv_carport_süd_kosten_jährlich
    + capex_pv_carport_süd_kosten_jährlich
    + opex_bs_kosten_jährlich
    + capex_bs_kosten_jährlich
)

prüfung_gesamtkosten_jährlich = network.objective

gesamtkosten_10_jahre = gesamtkosten_jährlich * 10

print(f"Die jährlichen Gesamtkosten betragen: {round(gesamtkosten_jährlich, 2)} €. Die Prüfung beträgt: {round(prüfung_gesamtkosten_jährlich, 2)} €")
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
network.links_t.p0["discharge_ladesäule_1"].plot()
network.links_t.p0["discharge_ladesäule_2"].plot()
network.links_t.p0["discharge_ladesäule_3"].plot()
network.links_t.p0["discharge_ladesäule_4"].plot()
network.links_t.p0["discharge_ladesäule_5"].plot()
network.links_t.p0["discharge_ladesäule_6"].plot()
network.links_t.p0["discharge_ladesäule_7"].plot()
network.links_t.p0["discharge_ladesäule_8"].plot()
network.links_t.p0["discharge_ladesäule_9"].plot()
network.links_t.p0["discharge_ladesäule_10"].plot()
network.links_t.p0["discharge_ladesäule_11"].plot()
network.links_t.p0["discharge_ladesäule_12"].plot()
network.links_t.p0["discharge_ladesäule_13"].plot()
network.links_t.p0["discharge_ladesäule_14"].plot()
network.links_t.p0["discharge_ladesäule_15"].plot()
network.links_t.p0["discharge_ladesäule_16"].plot()
network.links_t.p0["discharge_ladesäule_17"].plot()
network.links_t.p0["discharge_ladesäule_18"].plot()
network.links_t.p0["discharge_ladesäule_19"].plot()
#%%
network.stores_t.e["E-Bus_11_store"][0:700].plot()
network.stores_t.e["E-Bus_12_store"][0:700].plot()

# %%

network.generators_t.p["Einspeisung"].plot()
# %%
network.generators

# %%
network.stores.e_nom_opt["BS stationär"]
# %%
network.generators_t.p["Einspeisung"].sum()
#%%
network.generators_t.p["Einspeisung"].max()
# %%
# Alle discharge-Links der E-Busse herausfiltern
discharge_cols = network.links_t.p0.filter(like="discharge_ladesäule").columns

# Summe über alle Busse zu jedem Zeitschritt (= Gesamtleistung in kW)
discharge_summe = network.links_t.p0[discharge_cols].sum(axis=1)

# Plot der Summenleistung
discharge_summe.plot(title="Gesamte Rückspeiseleistung aus E-Bus-Flotte (bidirektionales Laden)")
plt.ylabel("kW")
plt.xlabel("Zeitschritt")
plt.show()
# %%
# Maximale gleichzeitige Rückspeiseleistung (kW)
discharge_max = discharge_summe.max()
print(f"Maximale Rückspeiseleistung: {round(discharge_max, 2)} kW")

# Gesamte durch bidirektionales Laden bereitgestellte Energie im Jahr (kWh)
# snapshot_weightings berücksichtigen, da 15-Min-Werte sonst zu hoch gewichtet werden
discharge_energie_jahr = (discharge_summe * network.snapshot_weightings.objective).sum()
print(f"Gesamte Energie durch bidirektionales Laden: {round(discharge_energie_jahr, 2)} kWh/Jahr")
# %%
network.generators_t.p["Stromnetz"].sum()
#%%
network.generators_t.p["Stromnetz"].max()

#%%

network.links_t.p0["discharge_ladesäule_19"][15000:18000].plot()

#%% Beispielzeitraum: 3 Grafiken untereinander (Snapshots 16850–16945) mit Uhrzeit-Beschriftung — Bus 9

import datetime

zeitraum = slice(16850, 16945)
snapshot_start = 16850

# Referenzzeit für die Beschriftung: 16850 entspricht Mo 12:00
start_time = datetime.datetime(2024, 1, 1, 12, 0)  # Datum beliebig, nur Uhrzeit/Wochentag-Logik relevant
tage_map = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}

# Tick-Positionen: alle 2 Stunden (=8 Snapshots à 15 Min), plus Endpunkt
tick_snapshots = list(np.arange(16850, 16946, 8))
if tick_snapshots[-1] != 16945:
    tick_snapshots.append(16945)

tick_labels = []
for s in tick_snapshots:
    delta_min = int((s - snapshot_start) * 15)
    t = start_time + datetime.timedelta(minutes=delta_min)
    tag = tage_map[t.weekday()]
    tick_labels.append(f"{tag} {t.strftime('%H:%M')}")

fig, axs = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

# ---------- Grafik 1: Speicherkapazität BS stationär + E-Bus_9 ----------

ax1 = axs[0]
ax1b = ax1.twinx()

ax1.plot(network.stores_t.e["BS stationär"][zeitraum], color="tab:blue", label="BS stationär")
ax1b.plot(network.stores_t.e["E-Bus_9_store"][zeitraum], color="tab:orange", label="E-Bus_9_store")

ax1.set_ylabel("BS stationär [kWh]", color="tab:blue")
ax1b.set_ylabel("E-Bus_9 [kWh]", color="tab:orange")
ax1.set_title("Speicherkapazität: stationärer Speicher & E-Bus 9")

lines1, labels1 = ax1.get_legend_handles_labels()
lines1b, labels1b = ax1b.get_legend_handles_labels()
ax1.legend(lines1 + lines1b, labels1 + labels1b, loc="upper left", fontsize=8)

# ---------- Grafik 2: bidirektionale Links Bus 9 + Anwesenheit ----------

ax2 = axs[1]
ax2b = ax2.twinx()

ax2.plot(network.links_t.p0["charge_ladesäule_9"][zeitraum], color="tab:green", label="Laden Bus 9")
ax2.plot(network.links_t.p0["discharge_ladesäule_9"][zeitraum], color="tab:red", label="Entladen Bus 9")
ax2b.plot(anwesenheit_ebus["Bus_9"][zeitraum], color="grey", linestyle="--", alpha=0.6, label="Anwesenheit Bus 9")

ax2.set_ylabel("Leistung [kW]")
ax2b.set_ylabel("Anwesenheit [0/1]")
ax2.set_title("Bidirektionales Laden Bus 9 & Anwesenheit")

lines2, labels2 = ax2.get_legend_handles_labels()
lines2b, labels2b = ax2b.get_legend_handles_labels()
ax2.legend(lines2 + lines2b, labels2 + labels2b, loc="upper left", fontsize=8)

# ---------- Grafik 3: PV gesamt, Netzbezug, Einspeisung, Strompreis ----------

ax3 = axs[2]
ax3b = ax3.twinx()

pv_gesamt = (
    network.generators_t.p["PV"]
    + network.generators_t.p["PV Carport Ost"]
    + network.generators_t.p["PV Carport West"]
)

ax3.plot(pv_gesamt[zeitraum], color="gold", label="PV gesamt")
ax3.plot(network.generators_t.p["Stromnetz"][zeitraum], color="tab:blue", label="Netzbezug")
ax3.plot(network.generators_t.p["Einspeisung"][zeitraum], color="tab:purple", label="Einspeisung")
ax3b.plot(dynamischer_strompreis[zeitraum], color="black", linestyle=":", label="Dyn. Strompreis")

ax3.set_ylabel("Leistung [kW]")
ax3b.set_ylabel("Strompreis [€/kWh]")
ax3.set_xlabel("Uhrzeit")
ax3.set_title("PV-Erzeugung, Netzbezug, Einspeisung & dynamischer Strompreis")

lines3, labels3 = ax3.get_legend_handles_labels()
lines3b, labels3b = ax3b.get_legend_handles_labels()
ax3.legend(lines3 + lines3b, labels3 + labels3b, loc="upper left", fontsize=8)

# x-Achse: Zeitraum begrenzen + Uhrzeit-Ticks auf allen Subplots setzen
for ax in axs:
    ax.set_xlim(16850, 16945)
    ax.set_xticks(tick_snapshots)

axs[-1].set_xticklabels(tick_labels, rotation=45, ha="right")

plt.tight_layout()
plt.show()


# %%







#Ab hier dauert die Berechnung wegen Sensitivität









#%% Sensitivitätsanalyse: statischer vs. dynamischer Strompreis

# 1. Baseline sichern (dynamisches Szenario muss vorher bereits optimiert worden sein)
kosten_dynamisch = network.objective
print(f"Systemkosten dynamischer Tarif: {round(kosten_dynamisch, 2)} €")

# 2. Zeitreihen-Preis am Generator "Stromnetz" entfernen, damit statischer Wert greift
network.generators_t.marginal_cost = network.generators_t.marginal_cost.drop(
    columns=["Stromnetz"], errors="ignore"
)

# 3. Schleife über statische Strompreise
statische_preise = np.arange(0.20, 0.46, 0.02)  # €/kWh, 20 bis 45 ct in 1-ct-Schritten

ergebnisse_preis = []

for preis in statische_preise:
    network.generators.loc["Stromnetz", "marginal_cost"] = preis
    status, cond = network.optimize(solver_name="gurobi")
    
    ergebnisse_preis.append({
        "strompreis_ct_kwh": preis * 100,
        "status": cond,
        "systemkosten": network.objective,
        "e_nom_opt_BS": network.stores.e_nom_opt["BS stationär"],
        "p_nom_opt_PV": network.generators.p_nom_opt["PV"],
    })

df_preis_sensitivität = pd.DataFrame(ergebnisse_preis)
df_preis_sensitivität

#%% Schnittpunkt näherungsweise bestimmen

diff = df_preis_sensitivität["systemkosten"] - kosten_dynamisch
schnittpunkt_idx = (diff.abs()).idxmin()
#schnittpunkt_preis = df_preis_sensitivität.loc[schnittpunkt_idx, "strompreis_ct_kwh"]
#print(f"Näherungsweiser Schnittpunkt bei ca. {schnittpunkt_preis} ct/kWh")

#%% Plot

plt.figure(figsize=(8,5))
plt.plot(df_preis_sensitivität["strompreis_ct_kwh"], df_preis_sensitivität["systemkosten"],
         marker="o", label="Statischer Tarif")
plt.axhline(kosten_dynamisch, color="red", linestyle="--", label="Dynamischer Tarif")
#plt.axvline(schnittpunkt_preis, color="grey", linestyle=":", label=f"Schnittpunkt ≈ {schnittpunkt_preis} ct/kWh")

plt.xlabel("Statischer Strompreis [ct/kWh]")
plt.ylabel("Jährliche Systemkosten [€]")
plt.title("Systemkosten: Statischer vs. dynamischer Strompreis")
plt.legend(loc="upper left", fontsize=8)
plt.tight_layout()
plt.show()
#%% Sensitivitätsanalyse: Batteriespeicherkosten (capex_bs)

capex_bs_werte = np.arange(100, 650, 50)  # €/kWh, 100 bis 600 in 50er-Schritten

ergebnisse = []

for capex_bs_test in capex_bs_werte:

    # Fixkosten für diesen capex_bs-Wert neu berechnen (gleiche Formel wie oben)
    capex_bs_anuity_test = (capex_bs_test / degradation_bs) * ((p * q**laufzeit) / (q**laufzeit - 1))
    opex_bs_test = 0.05 * capex_bs_anuity_test
    fixkosten_bs_test = capex_bs_anuity_test + opex_bs_test

    # Nur den capital_cost des Speichers im bestehenden Netzwerk überschreiben
    network.stores.loc["BS stationär", "capital_cost"] = fixkosten_bs_test

    # Neu optimieren
    status, cond = network.optimize(solver_name="gurobi")

    # Ergebnisse sichern
    ergebnisse.append({
        "capex_bs": capex_bs_test,
        "status": cond,
        "e_nom_opt_BS": network.stores.e_nom_opt["BS stationär"],
        "p_nom_opt_PV": network.generators.p_nom_opt["PV"],
        "p_nom_opt_PV_Ost": network.generators.p_nom_opt["PV Carport Ost"],
        "p_nom_opt_PV_West": network.generators.p_nom_opt["PV Carport West"],
        "gesamtkosten_jährlich": network.objective,
    })

df_sensitivität = pd.DataFrame(ergebnisse)
df_sensitivität
#%%
fig, ax1 = plt.subplots(figsize=(8,5))

ax1.plot(df_sensitivität["capex_bs"], df_sensitivität["gesamtkosten_jährlich"], marker="o", color="tab:blue")
ax1.set_xlabel("Speicherkosten capex_bs [€/kWh]")
ax1.set_ylabel("Jährliche Systemkosten [€]", color="tab:blue")

ax2 = ax1.twinx()
ax2.plot(df_sensitivität["capex_bs"], df_sensitivität["e_nom_opt_BS"], marker="s", color="tab:red")
ax2.set_ylabel("Optimale Speicherkapazität [kWh]", color="tab:red")

plt.title("Sensitivierung der Batteriespeicherkosten")
fig.tight_layout()
plt.show()
# %%

"""S18.3 check: where would a raw-PWM run at 300 s fall, given Sammy's 100, 200 and 500 s runs (11 Nov)?
One-lump model with Sammy's fitted chi_h, chi_c, tau. Writes docs/figures/module_08/s183_300s_vs_500s.png.
Run from the repository root: python3 python/analysis/s183_300s_check.py
"""
import numpy as np, csv, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
chih, chic, tau, U = 0.4175, 0.1494, 64.3, 50.0   # Sammy's fit to the 11 Nov raw run
def sim(P, n=12, dt=0.05):
    w=2*np.pi/P; t=np.arange(0,n*P,dt); th=0.0; out=np.empty_like(t)
    for i,tt in enumerate(t):
        u=U*np.sin(w*tt); chi=chih if u>=0 else chic
        th+=dt*(chi*u-th)/tau; out[i]=th
    m=t>=(n-4)*P; tt=t[m]; y=out[m]
    M=np.c_[np.ones_like(tt),np.cos(w*tt),np.sin(w*tt),np.cos(2*w*tt),np.sin(2*w*tt)]
    c=np.linalg.lstsq(M,y,rcond=None)[0]
    A1=np.hypot(c[1],c[2]); A2=np.hypot(c[3],c[4])
    # phase of T relative to PWM u = U sin(wt): T ~ A1 sin(wt - lag)
    lag=np.arctan2(-c[1],c[2])*-1
    lag=(np.arctan2(c[2],c[1])); lag=np.pi/2-lag   # sin(wt-d) = sin cos d - cos sin d -> c2=A cos d, c1=-A sin d
    d=np.arctan2(-c[1],c[2])
    return c[0],A1,d,A2/A1
rows=[]
for P in [100,200,300,500]:
    mean,A1,d,r2=sim(P); rows.append((P,mean,A1,d,r2)); print(P, round(mean,3), round(A1,3), round(d,3), round(r2,3))
meas={}
for r in csv.DictReader(open("data/module_08_sammy/s183_analysis_20261111_122227/s183_by_period.csv")):
    meas[int(r["period_s"])]=(float(r["mean_minus_baseline_C"]),float(r["A1_C"]),float(r["lag_rad"]),float(r["A2_over_A1"]),int(r["cycles_used"]))
print(meas)
Ps=np.arange(80,620,20); curves=np.array([sim(P,n=10,dt=0.1) for P in Ps])
fig,ax=plt.subplots(1,3,figsize=(13,3.8))
for k,(lab,j) in enumerate([("TEC amplitude A1 (°C)",1),("lag behind PWM (rad)",2),("2nd harmonic A2/A1",4)]):
    ax[k].plot(Ps,curves[:,j if j<4 else 3],"k-",lw=1,label="one-lump model (Sammy's fit)")
    mx=[p for p in sorted(meas)]; my=[meas[p][j if j<4 else 3] if j!=4 else meas[p][3] for p in mx]
    if j==1: my=[meas[p][1] for p in mx]
    if j==2: my=[meas[p][2] for p in mx]
    if j==4: my=[meas[p][3] for p in mx]
    ax[k].plot(mx,my,"o",color="C0",ms=7,label="measured 11 Nov")
    p3=[r for r in rows if r[0]==300][0]; ax[k].plot(300,p3[{1:2,2:3,4:4}[j]],"s",mfc="none",color="C3",ms=9,label="300 s, predicted")
    ax[k].set_xlabel("period (s)"); ax[k].set_title(lab,fontsize=10); ax[k].grid(alpha=.3); ax[k].set_xticks([100,200,300,400,500])
ax[0].legend(fontsize=8)
fig.suptitle("S18.3 raw PWM, u = 50 sin(ωt): what a 300 s run would add between Sammy's 200 s and 500 s",fontsize=10)
fig.tight_layout(); fig.savefig("docs/figures/module_08/s183_300s_vs_500s.png",dpi=120)

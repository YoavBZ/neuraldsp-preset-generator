import numpy as np
from scipy import stats
print("== Power: one-sample t on band means, SD 0.101, one-sided alpha")
for sd in (0.101,):
  for k in (3,5,6,7,8,9,10,12,15):
    df=k-1
    row=[]
    for eff in (0.05,0.08,0.10,0.13):
      nc=eff/(sd/np.sqrt(k))
      for a in (0.05,0.10):
        tc=stats.t.ppf(1-a,df)
        row.append(f"{eff:.2f}@a{a:.2f}:{1-stats.nct.cdf(tc,df,nc):.2f}")
    print(k, " ".join(row))
print()
print("== Two-sided 0.05 (90% CI upper<0 is one-sided 0.05) shown above; two-sided:")
for k in (8,9,12):
  df=k-1
  for eff in (0.05,0.10):
    nc=eff/(0.101/np.sqrt(k)); tc=stats.t.ppf(0.975,df)
    print(k,eff, round(1-stats.nct.cdf(tc,df,nc)+stats.nct.cdf(-tc,df,nc),2))
print()
print("== Bands needed for 80% power, one-sided 0.05")
for eff in (0.05,0.08,0.10):
  for k in range(3,80):
    df=k-1; nc=eff/(0.101/np.sqrt(k))
    if 1-stats.nct.cdf(stats.t.ppf(0.95,df),df,nc)>=0.8: print(eff,k); break
print()
print("== Exact binomial: decided trials n so that a one-sided test vs 0.5 at alpha 0.05 has >=80% power when true agreement=p")
for p in (0.9,0.8,0.75,0.7,0.65,0.6):
  for n in range(3,1000):
    # critical k: smallest k with P(X>=k|0.5)<=0.05
    ks=[k for k in range(n+1) if stats.binom.sf(k-1,n,0.5)<=0.05]
    if not ks: continue
    kc=ks[0]
    if stats.binom.sf(kc-1,n,p)>=0.8: print(p,n,"crit",kc); break
print()
print("== Alternative reading: n so that observing exactly the expected rate p*n gives p<0.05")
for p in (0.9,0.8,0.75,0.7,0.65,0.6):
  for n in range(3,1000):
    k=int(np.ceil(p*n))
    if stats.binom.sf(k-1,n,0.5)<=0.05: print(p,n); break
print()
c=0.8; print("max agreement for repeat consistency 0.8:", (1+np.sqrt(2*c-1))/2)
print("sign-flip min p:",[ (k,2**-k) for k in (3,5,6,7,9,12)])
print("17/21 binomial one-sided p:", stats.binom.sf(16,21,0.5), " 23/24:",stats.binom.sf(22,24,0.5), " 11/13:", stats.binom.sf(10,13,0.5)*2)
print()
print("== log ratio -> % closer:", {r: round(1-np.exp(r),3) for r in (-0.023,-0.05,-0.087,-0.10,-0.105,-0.129,-0.13,-0.15,-0.19,-0.26)})
print()
print("== Disk")
for sr in (44100,48000):
  for secs in (4,10):
    print(sr,secs,"s mono 16-bit MB:", sr*secs*2/1e6)
print("40k x 0.96MB GB:", 40000*0.96/1e3, " 43.3k:", 43300*0.96/1e3)
for bands,hop_ms,secs,b in ((128,10,10,4),(128,10,10,2),(128,10,4,2),(64,25,10,2),(128,20,10,2)):
  fr=int(secs*1000/hop_ms); sz=bands*fr*b
  print(f"logmel {bands}x{fr} {b}B = {sz/1e3:.0f} KB; x43.3k = {sz*43300/1e9:.1f} GB")
print()
print("== Render counts")
print("ladder 13 non-optional versions x 30 x 111:",13*30*111," reuse true DI:",12*30*111," +symbolic:",14*30*111)
print("ranker:",200*111, 100*111, 10000, 200*111+100*111+10000)
print("Sol bank 60k x 4 s hours of audio:",60000*4/3600)
print("Sol headroom 16x12x3:",16*12*3," x20 parts:",16*12*3*20, " product search 16x10x4:",16*10*4)
print("knob-ceiling: 25*111 + 75*2*450 =",25*111+75*2*450)
print("Mega-53 102s/30s on 21k 10-s clips hours:", 21000*(102/3)/3600)
print("65536 samples s @44.1k/48k:", 65536/44100, 65536/48000)
print("DAC 44k hop 512 fps:",44100/512)

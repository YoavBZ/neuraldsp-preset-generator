import sys, math, torch
sys.path.insert(0,'.'); sys.path.insert(0,'research')
torch.set_num_threads(1)
from learn import song_model as M, song_soundspace as SP
g = torch.Generator().manual_seed(0)
B, K, n, ns, nk = 16, M.K_MIX, len(M.CONT), len(M.SW), len(M.CAT)
logpi = torch.log_softmax(torch.randn(B,K,generator=g),-1); mu = torch.rand(B,K,n,generator=g); ls = torch.randn(B,K,n,generator=g).clamp(-3,0)
swl = torch.randn(B,ns,generator=g); catl=[torch.randn(B,len(M.MICS),generator=g) for _ in range(nk)]
out=(logpi,mu,ls,swl,catl)
c=torch.rand(B,n,generator=g)*0.9+0.05; cm=(torch.rand(B,n,generator=g)>0.3).float()
s=(torch.rand(B,ns,generator=g)>0.5).float(); sm=(torch.rand(B,ns,generator=g)>0.3).float()
k=torch.randint(0,len(M.MICS),(B,nk),generator=g); km=(torch.rand(B,nk,generator=g)>0.3).float()
b0=float(M.loss_fn(out,c,cm,s,sm,k,km))
def bt(Mm=1, sc=None, omega=None):
    d={"c":c[:,None].repeat(1,Mm,1),"sc":(cm if sc is None else sc)[:,None].repeat(1,Mm,1),"s":s[:,None].repeat(1,Mm,1),"ss":sm[:,None].repeat(1,Mm,1),"k":k[:,None].repeat(1,Mm,1),"km":km[:,None].repeat(1,Mm,1)}
    lw=torch.full((B,Mm),-math.inf); lw[:,0]=0; d["logw"]=lw; d["omega"]=torch.ones(B) if omega is None else omega; return d
print('B0', b0, 'gauss', float(SP.loss_soundspace(out,bt(),lp_fn=SP.gaussian_lp)), 'censored', float(SP.loss_soundspace(out,bt())))
print('padded 4', float(SP.loss_soundspace(out,bt(4))))
# two identical members at equal weight: should equal one member
d=bt(2); d["logw"]=torch.log(torch.tensor([[0.5,0.5]])).repeat(B,1); print('dup members', float(SP.loss_soundspace(out,d)))
# censored lp at limit equals tail mass
u=torch.tensor([0.0,1.0,0.5]); m=torch.tensor([0.2,0.7,0.5]); l=torch.log(torch.tensor([0.3,0.2,0.1]))
from scipy.stats import norm
print('cens', SP.censored_lp(u,m,l).tolist(), [math.log(norm.cdf(-0.2/0.3)), math.log(norm.sf((1-0.7)/0.2)), norm.logpdf(0.5,0.5,0.1)])

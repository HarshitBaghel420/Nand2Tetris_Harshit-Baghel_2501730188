#!/usr/bin/env python3
import sys,os,re;C={"0":"0101010","1":"0111111","-1":"0111010","D":"0001100","A":"0110000","!D":"0001101","!A":"0110001","-D":"0001111","-A":"0110011","D+1":"0011111","A+1":"0110111","D-1":"0001110","A-1":"0110010","D+A":"0000010","D-A":"0010011","A-D":"0000111","D&A":"0000000","D|A":"0010101","M":"1110000","!M":"1110001","-M":"1110011","M+1":"1110111","M-1":"1110010","D+M":"1000010","D-M":"1010011","M-D":"1000111","D&M":"1000000","D|M":"1010101"};J={"":"000","JGT":"001","JEQ":"010","JGE":"011","JLT":"100","JNE":"101","JLE":"110","JMP":"111"};P={k:v for k,v in zip("SP LCL ARG THIS THAT SCREEN KBD".split(),[0,1,2,3,4,16384,24576])};P.update({f"R{i}":i for i in range(16)});S=set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.$:")
class E(Exception):
 def __init__(s,n,m):super().__init__(f"Line {n}: {m}")
def c(l):return"".join(l.split("//")[0].split())
def i(n):return n and n[0].isalpha()or"_"in n or"$"in n or":"in n and all(ch in S for ch in n)
def d(e,n,t):
 if not e:return"000"
 if set(e)-{"A","D","M"}or len(e)!=len(set(e)):raise E(n,f"invalid instruction '{t}' (unknown destination '{e}')")
 return"".join("1"if x in e else"0"for x in"ADM")
def h(t,n):
 a,b,c="",t,""
 if"="in b:a,b=b.split("=",1)
 if";"in b:b,c=b.split(";",1)
 if b not in C:raise E(n,f"invalid instruction '{t}' (unknown computation '{b}')")
 if c not in J:raise E(n,f"invalid instruction '{t}' (unknown jump '{c}')")
 return"111"+C[b]+d(a,n,t)+J[c]
def p1(L,e):
 s=dict(P);o=[];n=1
 for r in L:
  t=c(r)
  if t:
   if t[0]=="(":
    if t[-1]!=")"or not i(t[1:-1]):e.append(str(E(n,f"invalid label '{t}'")));continue
    s[t[1:-1]]=len(o)
   else:o.append((n,t))
  n+=1
 return o,s
def p2(p,s,e):
 r=[];v=16
 for n,t in p:
  try:
   if t[0]=="@":
    x=t[1:]
    if x.isdigit():
     k=int(x)
     if k>32767:raise E(n,f"number too large in '{t}' (max 32767)")
    elif i(x):
     if x not in s:s[x]=v;v+=1
     k=s[x]
    else:raise E(n,f"invalid A-instruction '{t}'")
    r.append(f"{k:016b}")
   else:r.append(h(t,n))
  except E as z:e.append(str(z))
 return r
def a(src):
 e=[];p,s=p1(src.splitlines(),e);b=p2(p,s,e)
 e.sort(key=lambda m:int(re.search(r"Line (\d+)",m).group(1)));return b,e
def main(A):
 if len(A)not in(2,3)or not A[1].endswith(".asm"):print("Usage: python3 assembler.py Prog.asm [Out.hack]");return 2
 i=A[1];o=A[2]if len(A)==3 else i[:-4]+".hack"
 try:
  with open(i)as f:src=f.read()
 except OSError as z:print(f"Cannot open {i}: {z.strerror}");return 1
 b,e=a(src)
 if e:
  for m in e:print(m)
  print(f"{len(e)} error(s) found, {o} was not written.");return 1
 with open(o,"w")as f:f.write("\n".join(b)+"\n")
 print(f"Wrote {len(b)} instructions to {o}");return 0
if __name__=="__main__":sys.exit(main(sys.argv))
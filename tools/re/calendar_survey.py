import sys
# Levantamento das datas de cada competição brasileira e sul-americana no fm.exe.
# Uso: FM06_EXE=caminho/fm.exe python tools/re/calendar_survey.py
sys.path.insert(0, sys.argv[0].rsplit('/',1)[0])
from dates import dates, func
MONTH=['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
comps={
 'BRA_NAT_FIRST':(0xBBA400,0x7560A0),'BRA_NAT_SECOND':(0xBBA6A0,0x7560A0),'BRA_NAT_THIRD':(0xBBFD00,0xBBA900),
 'BRA_CUP':(0xBBAD30,0x7560A0),'BRA_STATE_LEAGUE':(0xBBB100,0xBB9EE0),'BRA_STATE_BAHIA':(0xBBE990,0xBBA240),
 'BRA_STATE_GAUCHO':(0xBBE030,0xBBA200),'BRA_STATE_PARA':(0xBBD750,0xBBA1B0),'BRA_STATE_PARAIBA':(0xBBBC90,0xBB9F10),
 'BRA_STATE_PARANA':(0xBBC270,0xBB9F50),'BRA_STATE_PERNAM':(0xBBCA10,0xBB9F80),'BRA_STATE_RIO':(0xBBF0A0,0xBBA270),
 'BRA_STATE_SANTA':(0xBBD120,0xBBA0D0),'BRA_STATE_TOCAN':(0xBBA940,0x7560A0),
 'SAM_LIBER_CUP':(0xC07980,0xC05CD0),'SAM_SUD_CUP':(0xC07380,0x7560A0),'SAM_SUPER_CUP':(0xC071D0,0x7560A0),
}
def region(a): return (0xBB2000<=a<0xBC2000) or (0xC04000<=a<0xC0A000)
def walk(va,seen,depth=0):
    if va in seen or va==0x7560A0: return
    seen.add(va)
    for r in dates(va):
        a=r[2]
        txt=' '.join('?' if v is None else (str(v) if v<0x100 else hex(v)) for v in a)
        print(f"   {'  '*depth}{r[0]:08X} -> {r[1]}  ({txt})")
    if depth<2:
        for i in func(va):
            if i.mnemonic=='call' and i.op_str.startswith('0x'):
                t=int(i.op_str,16)
                if region(t): walk(t,seen,depth+1)
for n,(m71,m72) in comps.items():
    print('==',n); seen=set(); walk(m71,seen); walk(m72,seen)

import struct,sys
sys.path.insert(0, __import__('os').environ.get('CAPSTONE_PATH',''))
import capstone
d=open(__import__('os').environ.get('FM06_EXE','workspace/fm.exe'),'rb').read()
B=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def func(va, limit=0x3000):
    ins=[]; prev_ret=False
    for i in md.disasm(d[va-B:va-B+limit],va):
        if i.mnemonic=='int3' and prev_ret: break
        ins.append(i); prev_ret = i.mnemonic.startswith('ret') or (i.mnemonic=='jmp' and prev_ret)
    return ins
def imm(op):
    try: return int(op,16) if op.startswith('0x') or op.startswith('-0x') else int(op)
    except: return None
REG8={'al':'eax','bl':'ebx','cl':'ecx','dl':'edx'}
def dates(va):
    res=[]; pushes=[]; regs={}
    for i in func(va):
        ops=[o.strip() for o in i.op_str.split(',')]
        if i.mnemonic=='xor' and len(ops)==2 and ops[0]==ops[1]:
            regs[REG8.get(ops[0],ops[0])]=0
        elif i.mnemonic=='mov' and len(ops)==2 and ops[0] in ('eax','ebx','ecx','edx','esi','edi','ebp','al','bl','cl','dl'):
            regs[REG8.get(ops[0],ops[0])]=imm(ops[1])
        if i.mnemonic=='push':
            v=imm(i.op_str)
            if v is None: v=regs.get(i.op_str)
            pushes.append((v, i.address))
        elif i.mnemonic=='call':
            vals=[p for p,_ in reversed(pushes)]  # arg1 first
            if any(v in (0x7d0,0x7d1) for v in vals[:6] if v is not None):
                res.append((i.address, i.op_str, vals[:6], pushes[-1][1] if pushes else 0))
            pushes=[]
        elif i.mnemonic in ('add',) and i.op_str.startswith('esp'):
            pushes=[]
    return res
if __name__=='__main__':
    for a in sys.argv[1:]:
        for r in dates(int(a,16)): print(f"{r[0]:08X} call {r[1]:>10}  args={['?' if v is None else hex(v) for v in r[2]]}")

"""Bounded Valve KeyValues text parser; retains order and repeated keys."""
import re
_TOKEN=re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')

def parse(text):
    if len(text)>16*1024*1024:raise ValueError('KeyValues input exceeds size limit')
    tokens=[];end=0
    for match in _TOKEN.finditer(text):
        if match.start()!=end:raise ValueError('Invalid or unterminated KeyValues string')
        end=match.end();t=match.group()
        if t.isspace() or t.startswith('//'):continue
        if t.startswith('"'):
            # Keep path backslashes literal except an escaped quote/backslash.
            t=re.sub(r'\\(["\\])',lambda m:m[1],t[1:-1])
        tokens.append(t)
    if end!=len(text):raise ValueError('Invalid KeyValues token')
    position=0
    def block(depth):
        nonlocal position
        if depth>64:raise ValueError('KeyValues nesting limit')
        result=[]
        while position<len(tokens):
            key=tokens[position];position+=1
            if key=='}':
                if not depth:raise ValueError('Unexpected closing brace')
                return result
            if key=='{' or position>=len(tokens):raise ValueError('Missing KeyValues value')
            value=tokens[position];position+=1
            if value=='{':value=block(depth+1)
            elif value=='}':raise ValueError('Missing KeyValues value')
            result.append((key,value))
        if depth:raise ValueError('Unclosed KeyValues block')
        return result
    return block(0)

def values(pairs):return {k.casefold():v for k,v in pairs if isinstance(v,str)}
def child(pairs,name):return next((v for k,v in pairs if k.casefold()==name.casefold() and isinstance(v,list)),[])

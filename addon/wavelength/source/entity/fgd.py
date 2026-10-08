"""Read common FGD classes/properties without evaluating FGD content as code."""
from pathlib import Path
import re

TOKEN=re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|[\[\]():=,@+]|[^\s\[\]():=,@+]+')

def load(path,seen=None,depth=0):
    path=Path(path).resolve();seen=set() if seen is None else seen
    if depth>16 or path in seen:raise ValueError('FGD include cycle or depth limit')
    if path.stat().st_size>4*1024*1024:raise ValueError('FGD exceeds 4 MiB limit')
    seen.add(path);text=path.read_text(encoding='utf-8-sig');tokens=[]
    for match in TOKEN.finditer(text):
        token=match.group()
        if not token.isspace() and not token.startswith('//'):tokens.append(token)
    i=0;classes={}
    def take():
        nonlocal i
        if i>=len(tokens):raise ValueError('Truncated FGD')
        value=tokens[i];i+=1;return value
    def value(token):return token[1:-1] if token.startswith('"') else token
    def balanced(opening,closing):
        nonlocal i
        if take()!=opening:raise ValueError('Invalid FGD block')
        count=1;result=[]
        while count:
            token=take()
            if token==opening:count+=1
            elif token==closing:count-=1
            if count:result.append(token)
        return result
    while i<len(tokens):
        if take()!='@':continue
        kind=take()
        if kind.lower()=='include':
            child=(path.parent/value(take())).resolve()
            if not child.is_relative_to(path.parent):raise ValueError('FGD includes must remain under the definition directory')
            classes.update(load(child,seen,depth+1));continue
        header=[]
        while i<len(tokens) and tokens[i]!='=':header.append(take())
        if i==len(tokens):raise ValueError('Missing FGD class name')
        take();name=take();description=''
        while i<len(tokens) and tokens[i]!='[':
            token=take()
            if token.startswith('"'):description+=value(token)
        body=balanced('[',']');properties=[];j=0
        while j<len(body):
            if j+3>=len(body) or body[j+1]!='(':
                j+=1;continue
            key=body[j];typ=body[j+2];j+=3
            while j<len(body) and body[j]!=')':j+=1
            j+=1;parts=[];choices=[]
            while j<len(body):
                if j+1<len(body) and body[j+1]=='(':break
                token=body[j];j+=1
                if token==':' and j<len(body):parts.append(value(body[j]));j+=1
                elif token=='[':
                    count=1;choice_tokens=[]
                    while j<len(body) and count:
                        t=body[j];j+=1
                        if t=='[':count+=1
                        if t==']':count-=1
                        if count:choice_tokens.append(t)
                    k=0
                    while k+2<len(choice_tokens):
                        if choice_tokens[k+1]==':':
                            code=value(choice_tokens[k]);label=value(choice_tokens[k+2]);k+=3
                            default='0'
                            if k+1<len(choice_tokens) and choice_tokens[k]==':':default=value(choice_tokens[k+1]);k+=2
                            choices.append((code,label,default))
                        else:k+=1
            properties.append({'key':key,'type':typ,'label':parts[0] if parts else key,'default':parts[1] if len(parts)>1 else '', 'choices':choices})
        bases=[]
        for n,t in enumerate(header):
            if t.lower()=='base' and n+1<len(header) and header[n+1]=='(':
                for base in header[n+2:]:
                    if base==')':break
                    if base!=',':bases.append(base)
        classes[name]={'kind':kind,'description':description,'bases':bases,'properties':properties}
    seen.remove(path)
    return classes

def properties(classes,name,stack=()):
    if name in stack:raise ValueError('FGD inheritance cycle')
    definition=classes.get(name,{})
    result={}
    for base in definition.get('bases',[]):result.update({p['key']:p for p in properties(classes,base,(*stack,name))})
    result.update({p['key']:p for p in definition.get('properties',[])})
    return list(result.values())


def entity_classes(classes):
    """Return concrete FGD entity classes suitable for the creation browser."""
    result=[]
    for name,definition in classes.items():
        kind=definition.get('kind','').casefold()
        if kind in {'pointclass','solidclass'}:
            result.append((name,definition.get('description',''),kind))
    return sorted(result,key=lambda item:item[0].casefold())

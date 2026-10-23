"""Read common FGD classes/properties without evaluating FGD content as code."""
from pathlib import Path
import re

TOKEN=re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|[\[\]():=,@+]|[^\s\[\]():=,@+]+')

def load(path,seen=None,depth=0,files=None):
    path=Path(path).resolve();seen=set() if seen is None else seen
    if depth>16 or path in seen:raise ValueError('FGD include cycle or depth limit')
    if path.stat().st_size>4*1024*1024:raise ValueError('FGD exceeds 4 MiB limit')
    if files is not None:files.add(path)
    seen.add(path)
    try:text=path.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:text=path.read_text(encoding='cp1252')
    tokens=[]
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
            classes.update(load(child,seen,depth+1,files));continue
        if kind.lower() not in {'baseclass','pointclass','solidclass','npcclass','filterclass','moveclass','keyframeclass'}:
            # @mapsize / @autovisgroup are editor directives, not class headers.
            while i<len(tokens) and tokens[i]!='@':i+=1
            continue
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
            key=body[j];typ=body[j+2];io=body[j-1].lower() if j and body[j-1].lower() in {'input','output'} else None;j+=3
            while j<len(body) and body[j]!=')':j+=1
            j+=1;parts=[];choices=[]
            while j<len(body):
                if j+1<len(body) and body[j+1]=='(':break
                token=body[j];j+=1
                if token==':':
                    # An omitted field is delimited by the next colon, not a
                    # literal ':' default. Do not consume the next property.
                    empty=j>=len(body) or body[j] in {':','[',']','='} or (j+1<len(body) and body[j+1]=='(')
                    parts.append('' if empty else value(body[j]))
                    if not empty:j+=1
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
            default=parts[1] if len(parts)>1 else ''
            if typ.lower()=='flags' and default=='':default=str(sum(int(code) for code,_,selected in choices if selected=='1'))
            if not io:properties.append({'key':key,'type':typ,'label':parts[0] if parts else key,'default':default, 'choices':choices})
        bases=[]
        for n,t in enumerate(header):
            if t.lower()=='base' and n+1<len(header) and header[n+1]=='(':
                for base in header[n+2:]:
                    if base==')':break
                    if base!=',':bases.append(base)
        classes[name]={'kind':kind,'description':description,'bases':bases,'properties':properties}
        for n,t in enumerate(header):
            if t.lower() in {'studio','studioprop'} and n+1<len(header) and header[n+1]=='(':
                model=header[n+2] if n+2<len(header) else ')'
                classes[name]['studio_model']=value(model) if model.startswith('"') else ''
                break
    seen.remove(path)
    return classes

def properties(classes,name,stack=()):
    if name in stack:raise ValueError('FGD inheritance cycle')
    definition=classes.get(name,{})
    result={}
    def merge(prop):
        previous=result.get(prop['key'])
        if previous and previous['type'].lower()==prop['type'].lower()=='flags':
            choices={c[0]:c for c in previous['choices']};choices.update({c[0]:c for c in prop['choices']})
            prop=dict(prop,choices=list(choices.values()),default=str(sum(int(code) for code,_,selected in choices.values() if selected=='1')))
        result[prop['key']]=prop
    for base in definition.get('bases',[]):
        for prop in properties(classes,base,(*stack,name)):merge(prop)
    for prop in definition.get('properties',[]):merge(prop)
    return list(result.values())


def studio_model(classes,name,stack=()):
    """FGD editor representation, independent of editable entity properties."""
    if name in stack:raise ValueError('FGD inheritance cycle')
    definition=classes.get(name,{})
    if definition.get('kind','').lower()=='solidclass':return ''
    if 'studio_model' in definition:return definition['studio_model']
    for base in reversed(definition.get('bases',[])):
        model=studio_model(classes,base,(*stack,name))
        if model:return model
    return ''


def entity_classes(classes):
    """Return concrete FGD entity classes suitable for the creation browser."""
    result=[]
    for name,definition in classes.items():
        kind=definition.get('kind','').casefold()
        if kind in {'pointclass','solidclass','npcclass','filterclass','moveclass','keyframeclass'}:
            result.append((name,definition.get('description',''),kind))
    return sorted(result,key=lambda item:item[0].casefold())

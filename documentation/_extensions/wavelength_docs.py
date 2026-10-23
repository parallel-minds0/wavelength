"""Screenshot placeholders, source links and live annotated source excerpts."""
import html,posixpath,re
from pathlib import Path
from docutils import nodes
from docutils.parsers.rst import Directive,directives

def source_file(root,value):
    path=(Path(root)/value).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError(f'Source file is missing or outside the repository: {value}')
    return path

def extract_region(text,name):
    start=f'# docs:begin {name}';end=f'# docs:end {name}'
    lines=text.splitlines()
    starts=[i for i,line in enumerate(lines) if line.strip()==start]
    ends=[i for i,line in enumerate(lines) if line.strip()==end]
    if len(starts)!=1 or len(ends)!=1 or ends[0]<=starts[0]:
        raise ValueError(f'Expected one ordered source region: {name}')
    import textwrap
    return textwrap.dedent('\n'.join(lines[starts[0]+1:ends[0]])),starts[0]+2

class CodeSample(Directive):
    required_arguments=2
    def run(self):
        env=self.state.document.settings.env
        try:
            path=source_file(env.config.wavelength_source_root,self.arguments[0])
            text,line=extract_region(path.read_text(encoding='utf-8'),self.arguments[1])
        except ValueError as exc:raise self.error(str(exc))
        env.note_dependency(str(path))
        label=nodes.paragraph('',f'{self.arguments[0]}:{line}')
        code=nodes.literal_block(text,text,language='python');code['linenos']=True
        return [label,code]

class Screenshot(Directive):
    required_arguments=1
    has_content=True
    option_spec={'alt':directives.unchanged_required}
    def run(self):
        env=self.state.document.settings.env;key=self.arguments[0]
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',key):raise self.error('Screenshot ID must use lowercase letters, digits and hyphens')
        path=Path(env.srcdir)/'screenshots'/f'{key}.png'
        env.note_dependency(str(path))
        if path.is_file():
            figure=nodes.figure();figure+=nodes.image(uri='/screenshots/'+path.name,alt=self.options.get('alt',key),width='100%')
            if self.content:figure+=nodes.caption('', ' '.join(self.content))
            return [figure]
        box=nodes.admonition(classes=['screenshot-placeholder'])
        box+=nodes.title('',f'Screenshot pending: {key}')
        box+=nodes.paragraph('',' '.join(self.content) or self.options.get('alt',key))
        box+=nodes.paragraph('',f'Capture file: documentation/screenshots/{key}.png')
        return [box]

def source_role(name,rawtext,text,lineno,inliner,options=None,content=None):
    env=inliner.document.settings.env
    match=re.fullmatch(r'(.+?)(?::(\d+))?',text)
    path,line=match.groups();line=line or '1'
    try:source_file(env.config.wavelength_source_root,path)
    except ValueError as exc:
        message=inliner.reporter.error(str(exc),line=lineno)
        return [inliner.problematic(rawtext,rawtext,message)],[message]
    if env.app.builder.format=='html':
        uri=posixpath.relpath('_static/code/'+path+'.html',posixpath.dirname(env.docname) or '.')+'#L'+line
        return [nodes.reference(rawtext,text,refuri=uri)],[]
    return [nodes.literal(rawtext,text)],[]

def setup(app):
    app.add_config_value('wavelength_source_root','', 'env')
    app.add_directive('code-sample',CodeSample)
    app.add_directive('screenshot',Screenshot)
    app.add_role('source',source_role)
    return {'version':'1','parallel_read_safe':True,'parallel_write_safe':True}

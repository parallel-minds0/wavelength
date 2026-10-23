"""Build the Markdown handbook without importing the Blender add-on."""
import json,os,sys,reportlab
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'_extensions'))
project='wavelength Handbook'
author='wavelength contributors'
metadata=json.loads((Path(__file__).parent/'book-metadata.json').read_text())
version=release=metadata['version']
extensions=['myst_parser','wavelength_docs','rst2pdf.pdfbuilder']
source_suffix={'.md':'markdown'}
root_doc='index'
exclude_patterns=['README.md','_code/**','screenshots/README.md','_extensions/**']
myst_enable_extensions=['colon_fence','deflist']
myst_heading_anchors=4
html_theme='alabaster'
html_static_path=['_static']
html_css_files=['handbook.css']
html_theme_options={'description':'User guide, engineering guide and source reference','fixed_sidebar':True}
html_sidebars={'**':['about.html','navigation.html','searchbox.html']}
html_title=f'wavelength {version} Handbook'
html_show_sourcelink=True
nitpicky=True
wavelength_source_root=os.environ['WAVELENGTH_DOCS_ROOT']
pdf_documents=[('index','wavelength-handbook',f'wavelength {version} Handbook',author)]
pdf_stylesheets=['sphinx','a4',str(Path(__file__).parent/'_static'/'book.yaml')]
pdf_font_path=[str(Path(reportlab.__file__).parent/'fonts')]
pdf_use_index=False
pdf_use_modindex=False
pdf_use_coverpage=True
pdf_use_toc=True
pdf_toc_depth=3
pdf_break_level=1
pdf_breakside='any'
pdf_language='en_US'
pdf_compressed=True
pdf_fit_mode='shrink'
pdf_splittables=True

# wavelength documentation

The current handbook starts at [handbook/index.md](handbook/index.md). Its User
Guide, Developer Guide and static code reference are generated from the canonical
repository `documentation/` sources by `python tools/docs.py sync`. Do not edit the generated
`handbook/` copy. Source installation and release packaging regenerate it.

HTML and a single PDF book are built with `python tools/docs.py build --format all`.
Screenshot placeholders are replaced when manual PNG captures are added to the
canonical `documentation/screenshots/` directory.

The older notes below are preserved as legacy documentation; use the handbook for
current workflows and implementation contracts.

- [Pre-alpha status](alpha-status.md)
- [Repository structure](repository-structure.md)
- [Architecture](architecture.md)
- [Development and testing](development.md)
- [Roadmap / TODO](todo.md)

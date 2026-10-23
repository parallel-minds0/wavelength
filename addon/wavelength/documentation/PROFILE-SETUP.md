# Profile setup and rendered asset thumbnails

Choose a Source 1 or GoldSrc profile and configure **Game Directory** and, where
needed, **Entity Definitions** under Scene Properties → Wavelength Map → Project
& Toolchain. Source needs gameinfo.txt and a valid game FGD; GoldSrc can also use
the stock entity mappings without an explicit FGD. Thumbnail preparation does not
require map compilers, though building maps still does.

Open **Scene Properties → Wavelength Map → Profile Setup**. With **Prepare Assets
Automatically** enabled, a configured profile enters setup after its paths settle.
The panel displays the current phase, progress, unavailable previews and cache
location. The existing **Use Local Toolchain** button still configures tool paths;
it is separate from content preparation.

The lifecycle is **Needs Configuration → Ready for Setup → Indexing → Preparing →
Ready**. You may browse while setup runs. **Pause** stops preparation and keeps
all cached work; **Start / Resume** continues it. **Cancel** also keeps cached
previews but disables automatic continuation until you start again. **Refresh**
rescans content and checks dependencies rather than forcing every image to render.
Disabling automatic preparation does not prevent an explicit Start command.

One hidden background Blender worker reads the installed game assets and renders
128-pixel, textured, shaded views from their actual geometry. The editor imports
only the thumbnail pixels into native asset previews. It does not load the entire
game's model library into your scene. Default entity representations and model
tiles share renders when model/skin/body/pose match. Abstract entities without
model geometry retain their normal fallback icons. Unsupported or missing models
are counted as unavailable; other previews continue. Details are in worker.log
inside the cache directory.

Both **Entities** and **Models** in the native Asset Browser display prepared
previews progressively. Searches prioritize matching remaining thumbnail jobs.
GoldSrc's Models catalog can assign an installed MDL to entities with an editable
model field, such as cycler. Fixed-model entities retain their game-defined
representation and are not given fake editable model properties.

The disk cache lives under `~/.cache/wavelength/libraries`, isolated by engine,
game installation and FGD path. Existing images are reused between sessions.
While the worker is active it checks mounted content for changes every 20 seconds;
changed models, textures, materials and model companions invalidate only dependent
previews. An archive update causes dependency checks, not blanket rerendering.
New or removed model names update an open Models catalog after the rescan.

Changing profiles or leaving/disabling Wavelength suspends its worker. Returning
resumes automatically unless you explicitly paused/cancelled. The worker also
exits after its parent Blender process closes. Cached previews stay usable while
paused and survive .blend saves. No game assets are bundled into Wavelength's
release; preparation reads your local installation.

Rendered thumbnails are representative editor images, not exact engine shader
rendering or animated turntables. A full initial library can take time; cached
revisits validate and reuse existing work.

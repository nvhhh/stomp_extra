# Third-party notices

## open-stomp

- Project: open-stomp (`open_stomp` Python package), https://github.com/JackMechem/open-stomp-lib
- Version used: 0.6.1
- Copyright (c) 2026 The open-stomp contributors
- License: MIT OR Apache-2.0, at the licensee's option. This project uses it under the MIT
  license. Both license texts are reproduced in [`licenses/open-stomp/`](licenses/open-stomp/).
  The project has no Apache-2.0 NOTICE file.

**How it is used.** The editor's NAM and IR import uses open-stomp to convert `.nam` models and
`.wav` cab IRs into the data the pedal plays:
- "Accurate" conversion is open-stomp's fitted (`optimised`) conversion.
- "Stomp Manager (original)" uses open-stomp's reimplementation of the official conversion.

This is in `nuxfw/namconv.py` and `nuxfw/irconv.py`. The pedal-side behavior these conversions
rely on (two 512-tap filters around a fixed saturation for NAM, 384 played taps for IRs) was
documented by the open-stomp project.

open-stomp is not bundled with this repository. `requirements.txt` installs its prebuilt
Windows wheel directly from the open-stomp GitHub release.

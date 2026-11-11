# Third-party software in the Docker images

The published images (`robotecai/agentic-mobile-manipulator`, `-ros2`, `-o3de`) contain the
pixi environments resolved in `pixi.lock`: **unmodified** binary packages from
[conda-forge](https://conda-forge.org) and [RoboStack](https://robostack.github.io)
(the `robostack-jazzy` channel). This project does not patch or rebuild any of them. Each
package is distributed under its own licence.

## Licence texts

Every image carries `/root/MobileManipulatorDemo/third_party_licenses/conda/`, written by
`pixi run collect-licenses` while the image is built:

- `<name>-<version>-<build>/`: the licence files shipped in that package;
- `PACKAGES.tsv`: every installed package with its version, its licence as declared by the
  package, the URL it was installed from, where its licence files are, and the recipe
  repository and commit it was built from.

RoboStack's `ros-jazzy-*` packages ship no licence text; their licence is listed by name in
`PACKAGES.tsv`, and the text is in the corresponding ROS repository.

## Source code

The source of every package is available from the channels it came from. The `recipe` and
`recipe_commit` columns of `PACKAGES.tsv` name the recipe each package was built from:

- conda-forge: the feedstock repository and commit (several packages can share one feedstock,
  e.g. `libgcc` comes from `ctng-compilers-feedstock`). The recipe pins the upstream source
  archive (URL and checksum) the package was built from. For the few older packages that
  record no recipe, their page on anaconda.org (`https://anaconda.org/conda-forge/<package>`)
  links the feedstock.
- RoboStack: <https://github.com/RoboStack/ros-jazzy>, whose generated recipes point to the
  ROS repositories and release tags the packages were built from.

## Copyleft components

- **ghostscript** (AGPL-3.0-only): a dependency of graphicsmagick, which `nav2_map_server`
  uses to load map images. GraphicsMagick only runs it for PostScript/PDF input, which the
  demo does not use, but every conda-forge graphicsmagick build declares it.
- **ffmpeg**: the LGPL-2.1-or-later build (without the GPL x264/x265 encoders); `pixi.toml`
  selects it.
- Other GPL and LGPL packages, unmodified, such as Qt 5 (LGPL-3.0), PyQt5 (GPL-3.0, used by
  the rqt tools), readline (GPL-3.0) and the GCC runtime libraries (GPL-3.0 with the GCC
  Runtime Library Exception). `PACKAGES.tsv` has the complete list.

The inference engines built from the git submodules (llama.cpp, FastFlowLM) and the
simulation assets are listed in [NOTICE](NOTICE).

# Arystal

Arystal simulates the growth of an amethyst crystal from the wall of a geode into a low-temperature hydrothermal fluid. Nothing is drawn: the facets, the iron sector pattern and the final shape come out of a phase-field model of the crystal surface coupled to silica diffusion and iron incorporation.

<!-- [TODO: GIF of a crystal growing, e.g. docs/media/growth.gif] -->

Version 1 is a two-dimensional engine written in Python (NumPy, with a Numba fast path) that runs on a single laptop CPU. The simulated section contains the crystal's c-axis, so it shows the prism and the pointed rhombohedral termination.

## Status

Phase 1 is complete. The engine runs live or saved simulations and ensembles, and passes 14 validation checks against theory, published data, conservation and numerical convergence.

The model is honest about what it does not know. The face growth speeds, the iron distribution coefficients and the colour law are assumed, so the simulated habit and colour contrast follow from those inputs and are not predictions about real amethyst. No run has yet been compared with a measured crystal. The full list of what is imposed and what is predicted is in the architecture document.

## Open question

Converting model time with published quartz rate laws gives 10⁷ to 10⁹ years for crystals of millimetres to centimetres, while the host basalts are about 135 million years old. This tension is unresolved; candidate explanations are discussed in `docs/growth_time.md`. Input from anyone working on silica geochemistry or geode formation is very welcome.

## Getting started

Arystal needs Python 3.12. The commands below create a virtual environment with [uv](https://docs.astral.sh/uv/) and install the dependencies:

```
git clone https://github.com/LunaFilosofa09/arystal.git
cd arystal
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
```

A first live run and a quick check of the fast kernels:

```
python scripts/run_live.py          # live window, explore size
python scripts/validate.py fast     # Numba vs reference (check 6)
```

Step-by-step instructions are in `docs/how_to_run.md`.

## Documentation

- **Architecture and design rationale** (PDF): `docs/engine_architecture/`. Start here to understand the physics, how the code is organised and why the main decisions were taken.
- `docs/how_to_run.md`: how to run simulations, saved runs and ensembles.
- `docs/function_map.md`: per-function listing of the package.
- `docs/validation_report.md`: what each validation check shows and does not show.
- `docs/parameter_audit.md`: source and status of every physical constant.

## Use of AI tools

I wrote some parts of the code myself, but most of it was written by Claude (Anthropic) through Claude Code. My role was to define and validate the physical model, design the studies and checks, and review every result, sending the code back for fixes whenever something didn't hold up. Every physical constant records its source and whether that source was read, estimated or assumed (`materials/amethyst.yaml`). Errors remain my responsibility.

## License

The source code is available under the [PolyForm Noncommercial License 1.0.0](LICENSE). You may use, study, modify and share it for any noncommercial purpose, including research, teaching and personal projects. Commercial use is not permitted without separate permission; if you are interested, open an issue or contact me.

The documentation in `docs/` is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), except the font files in `docs/engine_architecture/fonts/`, which keep their own GUST Font License.

Arystal is source-available rather than open source in the OSI sense, because of the noncommercial restriction.

## Author

Luna F. · [@LunaFilosofa09](https://github.com/LunaFilosofa09)

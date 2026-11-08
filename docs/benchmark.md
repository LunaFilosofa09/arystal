# Benchmark

Measured on Luna's MacBook Pro 2019 (Intel Core i7, 6 cores / 12 threads, 64 GB), Python 3.12, Numba 0.61.2, with `python scripts/benchmark.py`
(results saved in `results/benchmark.json`, which is git-ignored). "Full" model = iron, faceted growth and noise; "lean" = no iron, no noise.
Explicit diffusion (the original scheme). Milliseconds per time step; lower is better.

## One process

| Grid | Model | Reference (NumPy) | Numba, 1 thread | 2 threads | 4 threads | 6 threads |
|---|---|---|---|---|---|---|
| 200 x 100 | full | 2.81 | 1.40 | 1.10 | 0.88 | 0.76 |
| 200 x 100 | lean | 1.05 | 0.80 | 0.52 | 0.40 | 0.37 |
| 400 x 200 | full | 13.89 | 4.57 | 3.53 | 2.64 | 2.34 |
| 400 x 200 | lean | 3.63 | 2.56 | 1.55 | 1.15 | 1.07 |
| 800 x 400 | full | 80.49 | 22.76 | 17.16 | 13.92 | 14.14 |
| 800 x 400 | lean | 35.15 | 15.52 | 10.83 | 8.35 | 8.61 |

- The fast code is about **3x faster than the reference with one thread and 5-6x with 4-6 threads** (full model, 400 x 200 and 800 x 400).
- Beyond 4 threads there is little gain on large grids: the step is limited by memory traffic, not by arithmetic. 4 threads is a good default for a single run; the
  explore mode uses 4 and the research mode 6.
- What made the difference between the first Numba version (about 2x) and this one (about 3x single-thread): updating the crystal arrays (`crystal_iron` and the
  by-sector arrays) in place instead of copying them every step, and skipping the iron bookkeeping where the solid fraction does not change.
- The random numbers are drawn in single precision (they cost as much as the rest of the step with 6 threads otherwise).

## Several processes at the same time (ensembles), 1 thread each, full model, 400 x 200

| Processes | Seconds per process | Slowdown of each | Aggregate steps/s | Speed-up |
|---|---|---|---|---|
| 1 | 2.56 | 1.00 | 235 | 1.00 |
| 2 | 2.71 | 1.06 | 443 | 1.89 |
| 3 | 2.86 | 1.12 | 627 | 2.67 |
| 5 | 3.43 | 1.34 | 868 | 3.70 |
| 6 | 3.60 | 1.41 | 997 | 4.24 |

With 5 workers (the default) an ensemble is about **3.7x faster** than running the replicas one after the other. (With the earlier NumPy code,
the same 5 workers gave only 2.2x: that code was limited by memory bandwidth.) Replicas should use 1 thread each (the ensemble does).

## Cost of the physically justified regime (surface-limited growth)

The explicit scheme needs about 1/Da steps, which is millions of steps at the real Da (docs/kinetic_regime.md). Two exact-to-rounding changes of numerical scheme
(validated in check 6b) remove that cost without touching any physical parameter:

| Scheme | Time step | 200 x 100 crystal to radius 30 cells at Da = 6e-3 | Valid for |
|---|---|---|---|
| explicit | 0.2 (limited by the diffusion) | about 3 million steps (not run: hours) | any Da |
| implicit (backward Euler) | 0.1 tau, any size | 710 steps, 43 s (about 60 ms per step: a sparse factorisation each step) | any Da |
| uniform fluid (Da -> 0) | 0.1 tau | 710 steps, 0.5 s | Da much smaller than 1 (plateau, uniformity > 0.99) |

## The two modes (full model, with iron and noise, saving everything)

| Mode | Grid | Steps | Time |
|---|---|---|---|
| explore | 200 x 100 | 800 | about 4.5 s |
| research | 800 x 400 | 4000 | about 85 s (21 ms per step with 6 threads) |

Convergence runs (no iron, no noise, uniform fluid, 6 threads): 100 cells 0.2 s, 200 cells 0.3 s, 400 cells 1.4 s, 800 cells 20 s, 1600 cells 114-125 s.

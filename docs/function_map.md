# Function map

One line per module and function, so you can find your way around.

## Isotropic growth

### arystal/engine/isotropic_params.py
- `IsotropicParams` - all settings of a run (grid size, epsilon, driving force, time step, seed radius).

### arystal/engine/grid.py
- `compute_seed_center_x` - x position of the middle of the grid, where the seed sits.
- `compute_distance_to_seed_center` - distance of every cell to the seed centre on the wall.
- `create_half_disc_seed` - the starting phase field: a small half-disc of crystal on the wall.

### arystal/engine/phase_field.py
- `compute_laplacian` - how much each cell differs from its four neighbours (mirror at the edges).
- `compute_double_well_force` - the push of each cell towards crystal (1) or fluid (0).
- `compute_phase_field_rate` - d(phi)/dt: smoothing of the border plus the push.
- `advance_one_step` - moves the phase field forward by one time step.

### arystal/engine/isotropic_theory.py
- `compute_flat_front_speed` - exact growth speed of a flat front.
- `compute_critical_radius` - seeds smaller than this dissolve instead of growing.
- `compute_front_speed_at_radius` - exact growth speed of a curved (circular) front.

### arystal/metrics/shape.py
- `compute_crystal_area` - crystal area in cells.
- `compute_equivalent_radius` - radius of the half-disc with the same area.
- `sample_ray` - phase field values along a line from the seed centre.
- `find_surface_distance` - distance from the seed centre to the crystal surface along one angle.
- `measure_surface_radii` - surface distance for angles from 0 to 180 degrees.
- `compute_roundness_error` - spread of the radii relative to their mean (0 = perfect half-circle).

### arystal/simulation/isotropic_run.py
- `Snapshot` - state of the run at one moment (step, time, field, radius).
- `compute_maximum_radius` - largest radius before the crystal feels the domain edges.
- `create_initial_phase_field` - the seed for a given set of parameters.
- `make_snapshot` - packs the current state into a Snapshot.
- `iterate_growth` - runs the growth and hands out a Snapshot every few steps.

### arystal/viewer/live_view.py
- `build_title` - text above the picture.
- `create_window` - opens the live window with the first frame.
- `update_window` - redraws the window with a new snapshot.
- `save_final_picture` - saves a snapshot as PNG (no window needed).

### arystal/validation/isotropic_check.py (validation check 1)
- `collect_snapshots`, `select_speed_window` - run the growth and pick the part used for the speed measurement.
- `measure_growth_speed` / `predict_growth_speed` - measured speed vs. theory.
- `check_shape` - is the final crystal a half-circle?
- `check_speed` - does it grow at the predicted speed?
- `check_seed_is_supercritical` - is the seed big enough to survive?
- `run_isotropic_check` - runs all of the above.
- `format_report` - plain-text report.


## Silica, solubility, temperature

### arystal/engine/material_constants.py
- `MaterialConstants` - the constants of a material the engine needs (filled from the YAML file).

### arystal/engine/solubility.py
- `convert_celsius_to_kelvin` - C to K.
- `check_temperature_in_curve_range` - refuses temperatures where the solubility curve is not valid.
- `compute_equilibrium_concentration` - how much silica (mol/kg) the fluid can hold at equilibrium at a temperature.
- `convert_concentration_to_ppm` - mol/kg to ppm.
- `compute_supersaturation_ratio` - S = c / c_eq.
- `compute_dissolution_enthalpy_kj_per_mol` - heat of dissolution implied by the curve's slope (for check 4).

### arystal/engine/solution_params.py
- `SolutionParams` - all settings of a run with silica.
- `check_temperature_in_geode_range` - refuses temperatures outside the geode range (15-60 C).
- `create_solution_params` - builds the settings from a material, a run temperature and the temperature at which the fluid was saturated.

### arystal/engine/silica_transport.py
- `compute_solid_fraction` - h(phi): the solid share of each cell (0 fluid, 1 crystal).
- `compute_face_fluid_fraction` - fluid share on each face between neighbouring cells.
- `compute_flux_along_axis` - silica flowing through each face along one direction.
- `compute_diffusion_change` - net silica gained or lost by each cell through diffusion (closed boundaries).

### arystal/engine/solution_growth.py
- `SolutionState` - the two fields: phase field and silica.
- `create_initial_state` - seed on the wall in a uniform solution.
- `compute_driving_force` - m = lambda * ln(c / c_eq) for each cell.
- `compute_new_phase_field` - phase field after one step, pushed by the local supersaturation.
- `compute_new_silica` - silica after one step: diffusion minus what the crystal absorbed.
- `advance_one_step` - both fields one step forward.
- `compute_total_silica` - dissolved plus crystal silica (must stay constant).

### arystal/engine/time_scaling.py
- `compute_cell_size_mm` - physical size of a cell.
- `compute_model_time_unit_seconds` - seconds in one model time unit.
- `compute_real_solid_capacity` - silica capacity of real quartz (mol/kg).
- `compute_density_scaling_factor` - how many times lighter the model crystal is than a real one.
- `convert_model_time_to_diffusion_seconds` - model time to seconds (diffusion time scale).

### arystal/simulation/
- `material_loader.py`: `read_material_file`, `get_value`, `load_material` - reads materials/<name>.yaml.
- `solution_run.py`: `SolutionSnapshot`, `make_snapshot`, `iterate_solution_growth` - the run loop with snapshots.

### arystal/viewer/solution_view.py
- `build_title`, `compute_supersaturation_map`, `create_window`, `update_window`, `save_final_picture` - two-panel live window (crystal + supersaturation).

### arystal/validation/
- `check_result.py`: `CheckResult`, `format_report` - shared result type and plain-text report.
- `mass_check.py` (check 3): `check_scenario`, `compute_max_relative_drift`, `run_mass_check`.
- `solubility_check.py` (check 4): `check_value_at_room_temperature`, `check_inside_literature_spread`, `check_increases_with_temperature`, `check_enthalpy_consistency`, `check_range_is_enforced`, `run_solubility_check`.

## Amethyst shape (kinetic anisotropy)

### arystal/engine/anisotropy.py
- `FacetAnisotropy` - the speed polygon, cusp sharpness and cusp correction.
- `compute_face_normal_angles` - direction of the outward normal of each face (m, r, z, and mirrors) in the section.
- `get_face_speed` - speed of a face from its family name.
- `build_half_planes` - the faces as half-planes (normal and speed) for the polygon.
- `compute_polygon_vertices` - corners of the speed polygon (scipy half-space intersection).
- `find_missing_faces` - detects faces that would grow out and vanish.
- `create_facet_anisotropy` / `create_facet_anisotropy_from_material` - builds the anisotropy (refuses impossible speed sets).
- `compute_speed_factor_from_angle` - g(theta): relative growth speed of a surface with a given normal (smooth maximum).
- `compute_largest_speed_factor` / `compute_smallest_speed_factor` - extremes of g (for the stability check).

### arystal/engine/anisotropic_phase_field.py
- `compute_gradient` - slope of a field in x and y.
- `compute_outward_normal_angle` - direction the surface faces, out of the crystal.
- `compute_speed_factor_field` - g for every cell (1 in the bulk or when anisotropy is off).
- `advance_phase_field` - phase-field step with orientation-dependent speed (reused by the silica model).

### arystal/engine/solution_params.py (extended)
- `check_time_step_is_stable` - refuses a time step that is too large for diffusion or for the fastest orientation.

### arystal/metrics/symmetry.py
- `mirror_field_about_c_axis`, `compute_mirror_asymmetry`, `compute_crystal_mask`, `compute_area_asymmetry_fraction` - how mirror-symmetric the crystal is.

### arystal/metrics/facets.py
- `collect_interface_cells` - position and normal direction of every surface cell.
- `compute_angle_difference` - smallest difference between two angles.
- `measure_facet_distance` - distance of a flat face from the seed centre along its normal.

### arystal/validation/symmetry_check.py (validation check 2)
- `check_symmetry_with_equal_faces` - symmetric when r = z (full model).
- `check_symmetry_breaks_with_different_faces` - asymmetric when r and z differ.
- `run_constant_force_growth` - growth with a constant driving force (used by tests B and C).
- `compute_predicted_face_distance`, `build_face_list`, `measure_face_error`, `compute_apex_deficit` - Frank's construction vs the simulation.
- `check_frank_construction`, `run_symmetry_check` - the third test and the runner.

## Iron and color

### arystal/engine/iron_partition.py
- `SectorPartition` - incorporation coefficient of every face, plus the width of the transition between faces.
- `create_sector_partition` - builds it from the material constants.
- `compute_angle_distance` - smallest difference between two angles.
- `compute_partition_from_angle` - coefficient for a surface pointing in a given direction (smooth blend of the face coefficients).
- `compute_partition_field` - coefficient for every cell, from the surface direction there.

### arystal/engine/iron_incorporation.py
- `compute_fluid_iron_to_silica_ratio` - Fe/Si of the fluid in every cell.
- `compute_iron_taken_up` - iron that goes into the crystal in this step (coefficient x fluid Fe/Si x silica deposited).
- `compute_iron_given_back` - iron returned to the fluid by dissolving crystal.
- `compute_new_iron_fields` - fluid iron (diffusion + exchange) and crystal iron after one step.

### arystal/engine/solution_growth.py (extended)
- `advance_iron` - iron update, skipped when iron is switched off.
- `compute_total_iron` - dissolved plus locked-in iron (must stay constant).

### arystal/engine/solution_params.py (extended)
- `convert_iron_ppm_to_concentration` - ppm by mass to mol/kg.

### arystal/storage/rendering.py
- `compute_crystal_iron_ratio` - Fe/Si of the crystal in every cell.
- `compute_color_intensity` - saturating law: 1 - exp(-ratio / scale).
- `blend_colors` - pale quartz to deep amethyst.
- `render_crystal_rgb` - the coloured picture of the crystal.

### arystal/viewer/solution_view.py (extended)
- `build_crystal_picture` - left panel: coloured crystal when iron is simulated.

### arystal/validation/iron_check.py
- `check_iron_conservation` - iron conserved while growing and while dissolving.
- `check_iron_release_on_dissolution` - grow, then dissolve: iron comes back and is conserved.
- `compute_polar_angle_degrees`, `collect_sector_ratios`, `predict_coefficient`, `check_sector_zoning` - sector contrast vs the coefficients.
- `run_iron_check` - runs all of them.

## Noise, metrics, saved results, reproducibility

### arystal/engine/ (extended)
- `solution_growth.draw_seed_variation` - small random radius and position of the initial seed (from a random generator).
- `solution_growth.compute_noise_term` / `compute_new_phase_field(..., noise)` - random interface term sigma * sqrt(dt / tau) * 4 phi (1 - phi) * N(0,1).
- `metrics/shape.find_level_distance`, `compute_surface_roughness` - how ragged the contour phi = level is (used by the noise test).
- `grid.create_half_disc_seed(..., offset_x)` - seed that can sit slightly off-centre.
- `iron_partition.compute_face_weights`, `compute_family_weights_from_angle`, `compute_family_weight_field`, `compute_family_coefficients` - share of each face family (m, r, z) at every surface cell.
- `iron_incorporation.compute_family_deposits`, `compute_fraction_dissolved` - iron and silica deposited by each family; iron by sector is now recorded exactly.
- `regime_indicator.py` - `compute_model_damkohler` and helpers: attachment speed / diffusion speed of a configured run (goes into every summary).

### arystal/metrics/growth_metrics.py
- `collect_surface_points` - sub-cell positions of the crystal surface.
- `compute_support_distance` / `compute_face_distances` - how far the crystal extends in the direction of each face family (growth of m, r, z).
- `compute_height_and_width`, `compute_aspect_ratio` - length along c / width.
- `compute_estimated_mass_mg` - area x assumed thickness x real density.
- `compute_interface_supersaturation`, `compute_bulk_supersaturation` - S at the interface and in the fluid.
- `compute_mean_iron_ratio`, `compute_iron_ratio_by_sector` - iron in the crystal, total and per sector.

### arystal/simulation/
- `run_config.py`: `RunConfig` (all settings of a run), `create_config_from_dict` (rebuild from params.json).
- `seeded_run.py`: `create_rng_streams` (one seed -> two independent random streams), `build_params`, `compute_total_steps`, `prepare_run`, `draw_noise`.
- `metrics_recorder.py`: `MetricsRecorder.record` - one row of metrics (with rates and conservation drifts).
- `saved_run.py`: `run_and_save` (the whole run + results folder), `build_params_record`, `build_scientific_status` (caveats stored with every result), `build_summary`, `finish_run_folder`, `read_git_revision`.

### arystal/storage/
- `result_folder.py`: `create_result_folder` - results/<date>_<time>_<id>/ with snapshots/ and plots/.
- `serialization.py`: `to_jsonable`, `write_json`, `read_json`.
- `snapshots.py`: `save_snapshot`, `load_snapshot`, `list_snapshots`, `save_final_state`, `load_final_state`.
- `metrics_io.py`: `write_metrics_csv`, `read_metrics_csv`.
- `plots.py`: `save_metric_plots` - the PNG graphs of the metrics.
- `images.py`: `save_final_image` - final_image.png.

### arystal/validation/reproducibility_check.py
- `check_same_seed_identical`, `check_different_seeds_differ_slightly`, `check_saved_run` (results folder and replay), `check_noise_off_ignores_seed`, `check_noise_does_not_roughen_surface`, `run_reproducibility_check`.

## Live control and timeline

### arystal/engine/live_changes.py
- `change_temperature` - new temperature and the matching equilibrium silica (refuses temperatures outside 15-60 C).
- `set_fluid_iron` - sets the dissolved iron of the fluid to a new ppm value and returns the iron added.

### arystal/simulation/timeline.py
- `TimelineEvent` - one change: (step, time, parameter, value).
- `event_to_dict`, `event_from_dict`, `build_timeline_record`, `read_scheduled_events` - timeline.json reading and writing.

### arystal/simulation/controlled_run.py
- `ControlledRun` - the run that can be controlled: `request_pause`, `request_resume`, `request_stop`, `request_change` (queue requests);
  `process_commands` (applies them at the current step), `apply_change` / `apply_duration` (do and record a change), `advance` (compute steps, stopping at scheduled events),
  `is_finished`, `build_timeline_record`.
- `run_to_end` - run to the end without saving (events can be replayed).

### arystal/simulation/saved_run.py (extended)
- `RunSaver` - writes the run folder while the run advances (`sample`, `finish`), also for live sessions.
- `advance_and_sample` - advance a chunk and record metrics at the sampling steps.
- `run_and_save(..., scheduled_events)` - saved run, optionally replaying a timeline.
- `load_run_for_replay` - configuration and timeline of a saved run.

### arystal/viewer/control_panel.py
- `create_control_panel`, `update_control_panel`, `build_status_line`, `draw_pictures` - the window.
- `handle_temperature_change`, `handle_iron_change`, `handle_pause_click`, `handle_stop_click`, `handle_extend_click` - what each control does (plain functions, testable without a screen).

### arystal/validation/live_control_check.py
- `check_pause`, `check_temperature_response`, `check_timeline_and_replay`, `check_iron_change`, `check_extend_and_stop`, `check_refusals`, `check_window_controls`, `run_live_control_check`.

## Ensemble of replicas

### arystal/simulation/ensemble.py
- `EnsembleSettings` - number of replicas (10), parallel workers (5), base seed.
- `derive_replica_seeds` - distinct, reproducible seeds derived from the base seed.
- `build_replica_name` - folder name of a replica.
- `run_replica` - runs and saves one replica (top-level so it can run in another process).
- `build_jobs` - one plain-data job per replica (same settings and timeline, its own seed).
- `run_jobs` - runs the jobs in parallel in separate processes (or serially if workers = 1).
- `build_replica_records`, `build_ensemble_summary` - content of ensemble_summary.json.
- `run_ensemble` - the whole ensemble: folder, replicas, statistics, tables, pictures.

### arystal/metrics/ensemble_statistics.py
- `compute_statistics` - mean, standard deviation (n - 1), min, max of a list of values (ignores missing values).
- `compute_final_statistics` - the statistics of every metric over the final row of each replica.
- `rows_are_aligned`, `compute_timeseries_statistics` - mean and standard deviation over the replicas at every sampling moment.

### arystal/storage/ensemble_outputs.py
- `write_timeseries_csv` - ensemble_metrics.csv.
- `save_ensemble_plots` / `save_one_ensemble_plot` - mean +/- standard deviation graphs.
- `compute_common_crop` - the region that contains all crystals, so they are drawn at the same scale.
- `save_comparison_image` - comparison.png: the final crystals side by side.

### arystal/storage/result_folder.py (extended)
- `create_timestamped_name`, `create_ensemble_folder`; `create_result_folder(root, name)`.

### arystal/validation/ensemble_check.py
- `check_replica_equals_standalone`, `check_seeds`, `check_timeline_in_every_replica`, `check_outputs_and_statistics`, `check_serial_equals_parallel`, `check_statistics_function`, `run_ensemble_check`.

## Server

### arystal/server/app.py
- `create_app` - builds the FastAPI application (all routes; each depends on `authenticate`).
- `find_job_or_404`, `require_active_simulation` - answer 404 for unknown jobs and 409 for commands to jobs that cannot take them.
- `command_from_message` - turns a JSON message from the WebSocket into a job command (or refuses it).
- `send_frames`, `receive_commands` - the two halves of the WebSocket: frames out at a steady rate, commands in.

### arystal/server/job_manager.py
- `Job` - what the server knows about a job (status, latest frame, metrics history, cost, error).
- `JobManager` - `create_job` (starts the job in its own process; refuses if too many are active), `send_command`, `get_job`, `list_jobs`,
  `watch_jobs` / `read_events` / `apply_event` (follow the messages of the jobs), `check_process` (notices a process that died), `finish_job` (cost + notification), `shutdown`.

### arystal/server/job_worker.py (runs inside the job's own process)
- `job_process_main` - entry point; reports any failure instead of dying silently.
- `run_simulation_job` - a live-controlled simulation that streams frames and saves its results.
- `run_ensemble_job` - an ensemble from a saved run, reporting each replica.
- `apply_pending_commands`, `send_frame` (may drop), `send_important` (never dropped).

### arystal/server/frames.py
- `build_frame` - one frame: crystal picture, supersaturation picture, state and metrics.
- `build_crystal_picture`, `build_supersaturation_picture`, `encode_png_base64`, `downsample`, `sanitize_row`, `sanitize_value` (nan -> null).

### arystal/server/results_access.py
- `resolve_result_folder`, `resolve_result_file` - safe access (no leaving the results folder, only png/json/csv).
- `list_results`, `load_result`, `load_metrics`, `describe_run`, `describe_ensemble`, `classify_result`.
- `list_snapshot_steps`, `render_snapshot_png` - replay the animation from saved snapshots.

### arystal/server/schemas.py
- `JobRequest` (limits on every setting), `ParameterChange`, `EnsembleRequest`.

### arystal/server/notifications.py
- `notify_macos`, `build_notification_script`, `escape_for_applescript`, `should_notify`.

### arystal/server/authentication.py
- `authenticate` - the hook every route uses (accepts everyone for now).

### arystal/validation/server_check.py
- One function per test (`check_job_isolated_and_complete`, `check_control_and_replay`, `check_websocket_stream`, `check_refusals`, `check_results_access`, `check_ensemble_through_api`, `check_notifications`, `check_authentication_hook`), `run_safely`, `run_server_check`.

### test_page/index.html
- Minimal page: start a job, live pictures, sliders and buttons, metric graphs, past results. Not the real frontend.

## Speed, schemes, modes, studies

### arystal/engine/fast_kernels.py and fast_step.py (Numba)
- `phase_field_step_kernel` - the phase-field update (Laplacian, driving force, face anisotropy, noise) over all cells in parallel; `compute_speed_factor` - g(orientation).
- `transport_step_kernel` - silica (and iron) transport and iron incorporation by sector; `compute_diffusion_change`, `compute_family_shares` - its helpers.
- `advance_one_step_fast`, `advance_phase_field_fast`, `advance_transport_fast` - Python side: prepares arrays and calls the kernels (`in_place` updates the crystal arrays directly; `diffusion_scale` 0 switches diffusion off).
- `set_thread_count` - how many CPU threads the kernels use.

### arystal/engine/implicit_diffusion.py and uniform_fluid.py
- `build_diffusion_operator`, `solve_implicit_diffusion`, `advance_silica_implicit`, `advance_iron_implicit`, `suggest_implicit_time_step` - backward-Euler diffusion with a sparse direct solver.
- `advance_one_step_uniform` - the well-mixed limit (Da -> 0): uniform dissolved silica and iron recomputed from the conserved totals.
- `solution_growth.advance_one_step_implicit` and the dispatch by `params.diffusion_scheme` and `params.backend` in `advance_one_step`.
- `iron_incorporation.compute_iron_exchange` - the iron deposited/returned, separated from the diffusion.

### arystal/engine/time_scaling.py (extended)
- `compute_quartz_rate_constant`, `compute_real_front_speed`, `compute_kinetic_seconds_per_model_time` - the conversion of model time to real time through the verified quartz rate law.

### arystal/simulation/
- `modes.py`: `MODE_SETTINGS`, `build_mode_config`, `compute_relaxation_time`, `describe_mode` - explore (200 x 100) and research (800 x 400) on the plateau.
- `cli_options.py`: `add_run_options`, `config_from_arguments` - the options shared by the run scripts.
- `benchmarking.py`: `measure_milliseconds_per_step`, `benchmark_single_process`, `benchmark_parallel_processes` - speed measurements.
- `metrics_recorder.py`: `update_kinetic_time` - cumulative real time (`time_kinetic_years`).

### arystal/validation/
- `fast_vs_reference_check.py` (check 6): `run_both`, `check_scenario`, `check_thread_independence`, `measure_speed`.
- `implicit_check.py` (check 6b): `check_same_as_explicit`, `check_time_step_convergence`, `check_huge_step`, `check_dissolution`, `check_uniform_scheme`.
- `convergence_check.py` (check 5): `run_resolution`, `compute_changes`, `run_convergence_check`.
- `qualitative_check.py` (check 7): `time_to_reach_radius`, `check_growth_speed_rises_with_supersaturation`, `compute_solidity`, `report_facet_destabilisation`.
- `regime_study.py` (study): `build_study_params`, `grow_to_radius`, `run_regime_map`, `run_sensitivity`, `measure_crystal`, `compute_facet_fraction`, `compute_plateau_changes`.
- `check_result.py`: `CheckResult.informational` - measurements that are reported but do not decide pass or fail.

### scripts/
- `run_isotropic.py` - isotropic growth with the live window.
- `run_growth.py` - growth from a silica solution (live window, temperatures, duration, `--isotropic`, `--relaxation-time`, `--iron-ppm`).
- `validate.py` - runs validation checks `isotropic`, `symmetry`, `mass`, `iron`, `reproducibility`, `live`, `ensemble`, `server`, `fast`, `implicit`, `convergence`, `qualitative`, `solubility`, `ph_rate` or `all`.
- `run_saved.py` - runs a simulation and saves everything to results/<date>_<time>_<id>/ (also `--replay <folder>`, which repeats a run with its timeline).
- `benchmark.py` - speed of the simulation on this computer.
- `regime_study.py` - the regime map and the sensitivity table.
- `estimate_regime.py` - order-of-magnitude regime estimate from the rate law; a second table with the pH-dependent law (`describe_ph`, `print_ph_table`).
- `run_server.py` - starts the web server (local only, http://127.0.0.1:8000).
- `run_ensemble.py` - an ensemble of 10 replicas from a saved run (its settings and timeline), 5 parallel processes.
- `run_live.py` - live window with sliders (temperature, iron) and buttons (pause/resume, extend, stop and save); saves the run with its timeline.
- `estimate_regime.py` - order-of-magnitude estimate of diffusion- vs surface-limited growth (see kinetic_regime.md).

## pH-dependent quartz rate law (docs/kinetic_regime.md section 10)

### arystal/engine/ph_rate_law.py
- `compute_arrhenius_factor` - how much faster a reaction is at T than at 25 C, from its activation energy.
- `compute_neutral_rate_constant` - neutral-mechanism quartz rate constant at T (Palandri & Kharaka 2004).
- `compute_base_rate_constant` - hydroxide-catalysed rate constant at T and pH (3.16x per pH unit).
- `compute_ph_rate_constant` - neutral + base: the total rate constant at T and pH.
- `check_ph_in_range` - refuses a pH outside the range of the material file.

### Extended
- `engine/time_scaling.py`: `compute_quartz_rate_constant`, `compute_real_front_speed` take an optional `fluid_ph` (None = Takeno law).
- `engine/solution_params.py`: `SolutionParams.fluid_ph`, `create_solution_params(..., fluid_ph=...)`.
- `simulation/run_config.py`: `RunConfig.fluid_ph`; `cli_options.py`: `--fluid-ph`; `server/schemas.py`: `JobRequest.fluid_ph`.
- `simulation/saved_run.py`: `describe_rate_law` - the sentence in summary.json saying which rate law converted time.

### arystal/validation/ph_rate_check.py (check 4b)
- `check_neutral_term_at_25_celsius`, `check_base_term_at_25_celsius_ph_0`, `check_base_term_slope` - the code equals Table 4 of the source.
- `check_no_ph_keeps_takeno_law` - without pH nothing changes.
- `grow_small_crystal`, `check_ph_changes_only_real_time` - pH changes the real time, never the crystal.
- `check_ph_out_of_range_is_refused`, `run_ph_rate_check`.

## Face-speed study (docs/face_speed_study.md)

### arystal/validation/face_speed_study.py
- `build_material_with_speeds` - copy of the material with other m and z speeds.
- `build_research_params` - 800 x 400 parameters on the plateau, uniform fluid, iron on.
- `grow_until_size` - grows until the crystal reaches a given equivalent radius.
- `compute_sector_shares` - share of the crystal laid down by each face family.
- `measure_shape_and_iron` - aspect ratio, face ratios, iron and size of each sector.
- `run_case`, `list_cases` - one crystal per speed pair; the list of pairs.

### scripts/face_speed_study.py
- `print_row`, `plot_curves`, `plot_crystals`, `main` - runs the study and saves results/face_speed_study/.

## Plateau robustness (docs/regime_study.md section 7)

### arystal/validation/plateau_robustness.py
- `CASES` - the 12 conditions (temperature, size, face speeds, supersaturation, Cs_model), one change each.
- `build_case_params` - parameters of one case at a given tau.
- `run_case_at_tau` - grows the crystal of one case at one tau and records Da.
- `compute_mode_damkohler` - the nominal Da the modes would have in that case.
- `compute_relative_change`, `compute_one_cell_aspect_change` - helpers for the comparisons.
- `is_step_unchanged`, `find_plateau_onset` - where the shape stops changing as Da goes down.
- `check_aspect_within_one_cell`, `list_jobs`.

### scripts/plateau_robustness.py
- `start_worker`, `run_job`, `run_jobs` - 5 processes with 1 thread each.
- `summarise`, `plot_rows`, `main` (`--time-only`, `--summary-only`).

### scripts/facet_stability_probe.py (regime_study.md section 8)
- `build_probe_params`, `grow_with_noise`, `main` - larger crystals far from the plateau, with noise, to see whether faces cave in.

## Fluid renewal pulses (kinetic_regime.md section 11)
- `engine/live_changes.py`: `find_fluid_cells` (which cells hold fluid), `renew_fluid` (replace the fluid by fluid saturated at a temperature, count what is added).
- `simulation/controlled_run.py`: `compute_renewal_every_steps`; `ControlledRun.apply_renewal`, `is_periodic_renewal_due`, `apply_due_periodic_renewal`; `injected_silica`.
- `simulation/timeline.py`: `RENEWAL` event; `run_config.py`: `renewal_interval`, `renewal_saturation_celsius`; CLI `--renewal-interval`, `--renewal-saturation`; server fields of the same names.
- `validation/renewal_check.py`: `compute_total_silica`, `compute_total_iron`, `check_single_renewal`, `grow_closed_and_renewed`, `check_periodic_renewal`, `check_out_of_range_refused`, `build_uniform_config`, `run_renewal_check`.

## Comparison with observations (docs/observation_comparison.md)

### arystal/comparison/observed.py
- `ObservedMeasurement`, `ObservedSample` - a measured quantity (value, uncertainty, role) and a sample.
- `check_role`, `build_measurement`, `load_observed_sample` - read and check an observation YAML file.

### arystal/comparison/simulated.py
- `read_last_metrics_row`, `read_params` - read a saved run.
- `compute_section_angles` - interior angles of the section from the crystallography.
- `compute_sector_area_shares` - share of the crystal grown by each face family.
- `compute_color_intensity` - colour intensity of a sector from its Fe/Si (ASSUMED colour law).
- `measure_simulated_quantities` - every comparable quantity of a run.
- `get_numerical_uncertainty` - the model's own numerical error of a quantity (from check 5).

### arystal/comparison/compare.py
- `ComparisonRow`, `compute_tolerance`, `compare_one`, `compare_sample` - observed vs simulated with a tolerance.
- `summarise_by_role`, `describe_validation_status` - keeps checks, calibrations and predictions apart, and says what can be claimed.

### scripts/compare_with_observation.py
- `parse_arguments`, `format_row`, `print_table`, `write_csv`, `find_observed_image`, `plot_bars`, `plot_comparison`, `main`.


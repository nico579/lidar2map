***English** | [Français](README.fr.md)*

# lidar2map documentation

The main [README](../README.md) explains what lidar2map is and gets you to a
first map quickly. This index points to the canonical page for each topic. A
technical fact should be maintained in one page only; the other pages link to
it instead of duplicating it.

## Start here

| Need | Canonical guide |
|---|---|
| Install lidar2map and create a first map | [Getting started](getting-started.md) |
| Use every command-line workflow | [CLI reference](cli.md) |
| Choose a relief visualization | [LiDAR visualizations](shadings.md) |
| Pick the right phone/GIS format | [Formats and applications](formats.md) |
| Check countries, resolution, accounts and keys | [Providers and coverage](providers.md) |
| Run, resume or stop a job on an Ubuntu VM | [Remote execution](remote.md) |

## Advanced use

| Topic | Guide |
|---|---|
| Standing structures and classified point clouds | [DFM, LAZ and CSF](dfm.md) |
| Build, package, update and troubleshoot the application | [Build and deployment](../BUILD.md) *(currently in French)* |
| Evaluated elevation sources, including rejected ones | [LiDAR provider roadmap](lidar_providers_roadmap.md) |
| Data sources, licences and acknowledgements | [Data licences](data-licenses.md) |

## Contributing

- [Add or maintain a LiDAR provider](contributing-providers.md)
- [Open an issue](https://github.com/nico579/lidar2map/issues) for a bug,
  unsupported area or documentation problem.
- The code is licensed under [GNU GPL v3](../LICENSE).

## Engineering records

The following pages preserve design reviews and implementation investigations.
They are useful to maintainers, but they are not current user instructions:

- [LAZ / DFM / CSF review log](dfm_reviews.md)
- [Remote-execution unification design record](evolution_execution_distante.md)
- [Python 3.12 bootstrap investigation](correctif_bootstrap_python312_multiplateforme.md)
- [Warp, overview and MBTiles parallelism investigation](correctif_parallelisation_warp_overviews_mbtiles.md)

When an engineering record conflicts with a user guide, the user guide and the
current program help are authoritative.


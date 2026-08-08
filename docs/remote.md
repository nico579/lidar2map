# Run lidar2map on an Ubuntu VM

***English** | [Français](remote.fr.md) · [Documentation index](../README.md#documentation)*

lidar2map includes two remote modes for x86-64 virtual machines running Ubuntu
24.04 LTS or Ubuntu 26.04 LTS. They work with any cloud provider and with a
local VM:

- `--remote-gui` prepares an XFCE desktop reachable through RDP and installs
  the full graphical application;
- `--remote-cli` runs a headless job in `tmux`, monitors it, and progressively
  synchronizes its results to the local computer.

The commands below use `lidar2map` for readability. Use `lidar2map.exe` on
Windows, `./lidar2map` on Linux, or `python lidar2map.py` from the sources.

## Start with the integrated modes

Prepare a graphical desktop and open the local RDP client:

```bash
lidar2map --remote-gui --ip 192.0.2.10
```

Run a headless job from the published Linux bundle:

```bash
lidar2map --remote-cli --bundle --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --provider fr-ign --zone-city Paris --zone-width 5 --download \
  --shading lrm:sigma=3 --file-formats mbtiles
```

Everything after the standalone `--` is passed unchanged to lidar2map on the
VM. The remote controller reserves `--output-dir` so every session has an
isolated directory that can be synchronized safely.

No separate remote archive is required: both controllers ship in every normal
lidar2map release.

| Mode | Use it when | VM setup |
|---|---|---|
| `lidar2map --remote-gui` | You want the complete GUI through a remote desktop | XFCE, xrdp, Xorg, Qt/XCB libraries, and lidar2map |
| `lidar2map --remote-cli` | You want unattended, reconnectable jobs and local result synchronization | Only headless tools required by the selected source/bundle mode |

## Common requirements

The VM must be new or in a coherent state, reachable through SSH, and able to
access the Internet. The local Windows, Linux, or macOS computer must provide
the OpenSSH `ssh` client. GUI mode also uses `scp` and `ssh-keygen`.

Authentication can use the administrator password or a private key. A key is
recommended to avoid repeated password prompts. Provisioning runs as `root` or
as an account with non-interactive `sudo`.

Open only the ports that are needed:

- TCP 22 for SSH in both modes;
- TCP 3389 for GUI/RDP mode, preferably restricted to the local computer's
  public IP address.

### Prepare an SSH key

The simplest option is to add the local computer's public key while creating
the VM. For an existing VM, use the instructions for the local platform.

**Windows.** OpenSSH normally uses `%USERPROFILE%\.ssh\id_ed25519`. Create it
if necessary:

```powershell
ssh-keygen -t ed25519
```

**WSL.** WSL has a filesystem separate from the Windows host. Copy the Windows
key into WSL's native filesystem; do not point SSH directly at `/mnt/c/...`,
whose NTFS permissions are too broad and trigger “UNPROTECTED PRIVATE KEY
FILE”:

```bash
mkdir -p ~/.ssh
cp /mnt/c/Users/<user>/.ssh/id_ed25519     ~/.ssh/id_ed25519
cp /mnt/c/Users/<user>/.ssh/id_ed25519.pub ~/.ssh/id_ed25519.pub
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

**Native macOS or Linux.** On a physically separate computer, prefer creating
a new key to copying a private key between machines:

```bash
ssh-keygen -t ed25519
ssh-copy-id root@<VM_IP>
```

`ssh-copy-id` works while the root password is enabled and asks for it once. If
password login is disabled, add the public key from a computer that is already
trusted by the VM:

```bash
ssh root@<VM_IP> "echo '<contents of id_ed25519.pub>' >> ~/.ssh/authorized_keys"
```

Keys in the standard location are detected automatically. Use `--identity`
only for a key stored elsewhere.

## Graphical mode: XFCE and RDP

The integrated command is:

```bash
lidar2map --remote-gui --ip 192.0.2.10
```

When launched without options, the controller asks for the VM IP address. The
defaults are:

- SSH administrator: `root`;
- Linux/RDP account created on the VM: `userlidar`;
- initial password: `userlidar`;
- SSH key: the local OpenSSH default.

All output, including `ssh`, `scp`, and the Ubuntu installer, is appended to
`rlidar2map_GUI.log` next to the executable. If that directory is not writable,
the controller falls back to the current or temporary directory. On Windows,
the window remains open after an error so the diagnostic and log location can
be read.

The controller removes the old SSH fingerprint for the IP, accepts the new
one, copies the provisioning script, and runs it. It installs XFCE, xrdp, Xorg,
the Qt/XCB libraries, the latest lidar2map release, and a secured desktop
shortcut. On Ubuntu 26.04 it also isolates the compatibility Qt libraries
needed for keyboard input.

The shortcut uses XFCE startup notification: after a double-click, the pointer
remains busy until the Qt window appears or the desktop safety timeout expires.

At the end, the local RDP client opens automatically:

- Windows: Remote Desktop Connection (`mstsc`);
- Linux: FreeRDP, or Remmina when FreeRDP is absent;
- macOS: Windows App through a generated `.rdp` file.

Log in initially as `userlidar/userlidar`, then change the password:

```bash
ssh -t userlidar@192.0.2.10 passwd
```

Advanced options:

```text
lidar2map --remote-gui --help
lidar2map --remote-gui --ip 192.0.2.10 --identity ~/.ssh/id_ed25519
lidar2map --remote-gui --ip 192.0.2.10 --ssh-user root --user userlidar
lidar2map --remote-gui --ip 192.0.2.10 --upgrade-system
lidar2map --remote-gui --ip 192.0.2.10 --no-rdp
```

`--upgrade-system` is optional. APT package lists are always refreshed, but a
full Ubuntu upgrade is not required. `--no-rdp` provisions the VM without
opening a local RDP client.

The bundled controller contains `rlidar2map_GUI_vm.sh`, extracts it temporarily,
forces Unix LF line endings even when the release was built on Windows, and
copies it to the VM. There is nothing to download or execute manually. The
detailed APT log remains on the VM at `/var/log/rlidar2map_GUI_apt.log`.

## Headless CLI mode

CLI mode installs neither XFCE nor xrdp and does not require port 3389. On the
first run it installs only missing packages with APT: `tmux` and, according to
the selected mode, `git`, `python3`, `python3-venv`, `curl`, or `rsync`. It runs
`apt-get update`, never a full Ubuntu upgrade.

### Bundle or source

- `--bundle` downloads and uses the published Linux x86-64 lidar2map bundle;
- `--source` clones or updates the source checkout and bootstraps its Python
  environment. It is the default.

The source checkout, virtual environment, bundle runtime, `cache/`, and
`production/` are shared resources on the VM. Per-run state, logs, and results
are isolated by session.

### Sessions and run IDs

The VM stores persistent state under `~/.lidar2map-runs/<session>`. Although the
default session is `lidar`, use an explicit, descriptive `--session` for every
job. Concurrent jobs on one VM must use different session names.

Each launch also receives a unique `run-id`. Results are copied locally under:

```text
vm-results/<host>/<session>/<run-id>/
```

`--local-dir` changes the local root. The controller-injected `--output-dir`
keeps remote results and logs isolated. Reusing an existing session never
starts a second job implicitly.

### Monitoring, detach, reconnect, and one-shot synchronization

Continuous monitoring is the default. Every 30 seconds the controller reads
the atomic remote state, shows live log progress, and synchronizes published
files. At terminal state it performs the final synchronization and reports the
real exit code. State, exit code, and timestamps from the `tmux` wrapper are
authoritative; success is never inferred by parsing log text. A normal exit,
crash, or vanished `tmux` session is reported.

Close the local monitor without stopping the remote job with `Ctrl+C` and
answer **No** when asked whether to stop it, or launch detached from the start:

```bash
lidar2map --remote-cli --bundle --detach --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --provider fr-ign --zone-city Paris --zone-width 5 --download \
  --shading lrm:sigma=3 --file-formats mbtiles
```

Reconnect without repeating the lidar2map arguments:

```bash
lidar2map --remote-cli --session paris-lrm root@192.0.2.10
```

The existing run is monitored and synchronized; no second calculation is
created. `tmux` retains terminal state after the monitor closes, so a later
reconnection performs any pending final copy. The controller also prints a
direct `tmux attach` hint for interactive diagnosis.

`--once` performs one state check and one synchronization, then returns:

```bash
lidar2map --remote-cli --once --session paris-lrm root@192.0.2.10
```

`--interval SECONDS` changes the 30-second cadence. `--max-ssh-errors` changes
the default tolerance of three consecutive SSH or local-monitoring errors.
`--no-bell` disables the terminal completion/error bell.

### Synchronization details and `--sync-only`

With `--sync-method auto`, rsync is preferred when available at both ends.
Otherwise the client uses an incremental SSH stream (`ssh` and `scp` select the
same fallback) with SHA-256 verification and atomic local publication.

Files and directories ending in `.part` and auxiliary SQLite files are ignored.
During an active run, the fallback requires the inventory to be identical twice
before transfer. Pure `.vrt` intermediates are never copied. The full run log is
copied atomically once the run becomes terminal.

`--sync-only` limits result categories copied locally:

| Value | Files copied |
|---|---|
| `ombrages` | Intermediate shading GeoTIFFs (`.tif`) |
| `carte` | Tiled maps (`.mbtiles`, `.rmap`, `.sqlitedb`) |
| `tout` | All published result types; this is the default |

Example:

```bash
lidar2map --remote-cli --session paris-lrm --sync-only carte \
  root@192.0.2.10
```

`--sync-method` accepts `auto`, `rsync`, `ssh`, or `scp`. A file transferred by
the fallback is checked by SHA-256 before it replaces its local destination.

### Resume versus restart

A terminal session is never relaunched implicitly.

- `--resume` reruns the **same lidar2map arguments in the same run**, without
  archiving or deleting its results. Its `run-id` remains unchanged. Existing
  downloaded tiles remain cached; only missing or failed data needs to be
  downloaded again. This is appropriate after a transient network failure and
  is allowed only for a terminal session, never an active one.
- `--restart` archives the terminal state and results, creates a new run, and
  uses the arguments supplied after `--`. Use it for a real parameter change.

Repeat the original arguments for `--resume`. The controller requires an
argument list but does not compare it automatically with the preceding run;
copy the printed reconnect/resume command rather than reconstructing it from
memory:

```bash
lidar2map --remote-cli --bundle --resume --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --provider fr-ign --zone-city Paris --zone-width 5 --download \
  --shading lrm:sigma=3 --file-formats mbtiles
```

Restart with new parameters:

```bash
lidar2map --remote-cli --bundle --restart --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --provider fr-ign --zone-city Paris --zone-width 5 --download \
  --shading svf:dist=20,gamma=2 --file-formats mbtiles
```

### Ctrl+C, targeted stop, and file retention

During continuous monitoring, `Ctrl+C` asks two independent questions:

1. whether to stop the process belonging to this exact session on the VM;
2. if it was stopped, whether to purge that session's remote files.

Answering **No** to the first question stops only the local monitor; the remote
`tmux` job continues. Answering **No** to the purge keeps its state, log,
results, and shared cache for later reconnection or `--resume`.

To stop one session non-interactively without touching concurrent sessions:

```bash
lidar2map --remote-cli --session paris-lrm --stop root@192.0.2.10
```

`--stop` sends Ctrl+C to that session so lidar2map can close its manifest,
`.part` files, and SQLite databases cleanly. After a 15-second grace period it
kills only that pane's descendant process tree and its `tmux` session if still
necessary. A stop during provisioning similarly terminates only that session's
bootstrap descendants. The terminal state is recorded with exit code 130 when
the runner cannot publish it itself. `--stop` does not purge files and accepts
no lidar2map arguments.

### Safe remote purge

The recommended explicit purge command is:

```bash
lidar2map --remote-cli --session paris-lrm --purge-remote root@192.0.2.10
```

It is accepted only when the run is terminal and no `tmux` session remains. It:

1. performs a final local synchronization;
2. cancels deletion if that synchronization is incomplete;
3. records the exact `session` and `run-id` copied;
4. verifies that the remote target still has that same `run-id` immediately
   before deletion;
5. removes only that run's state, log, and isolated results.

If another run has replaced it between copy and purge, no new run or archive is
deleted. The operation is recoverable/idempotent if the SSH purge response is
lost. The complete local copy remains in `vm-results`.

Shared `cache/`, `production/`, the source checkout, virtual environment, and
bundle runtime are never deleted. They remain available to another run or to a
future `--resume`.

The final synchronization obeys `--sync-only`. Its default, `tout`, preserves
every published result type before deletion; do not select a narrower category
if the local copy must be a complete backup.

The immediate purge offered after Ctrl+C explicitly warns that unsynchronized
results may be lost. To guarantee the final synchronization, answer **No** to
that purge prompt, then run the explicit `--purge-remote` command above.

### Controller option summary

| Option | Default / role |
|---|---|
| `VM` | Required SSH target: `user@host`, IP address, or `~/.ssh/config` alias |
| `--source` / `--bundle` | Source checkout is the default; the alternatives are mutually exclusive |
| `-s`, `--session NAME` | Persistent `tmux`/run identity; default `lidar`, explicit name strongly recommended |
| `--local-dir DIR` | Changes the local `vm-results` root |
| `--interval SECONDS` | Monitor/sync interval, default 30 |
| `--sync-method METHOD` | `auto`, `rsync`, `ssh`, or `scp`; auto prefers rsync |
| `--sync-only CATEGORY` | `ombrages`, `carte`, or `tout` |
| `--identity FILE` | Private SSH key; otherwise normal OpenSSH config/agent applies |
| `--ssh-timeout SECONDS` | Per-command timeout, default 10 |
| `--ssh-option KEY=VALUE` | Extra repeatable OpenSSH option |
| `--reset-host-key` | Forces proactive removal of the target's old `known_hosts` key; normally a detected change is repaired automatically |
| `--max-ssh-errors N` | Consecutive errors tolerated, default 3 |
| `--no-bell` | Disables the terminal bell |
| `--detach` | Launches or finds the run, synchronizes, and returns without continuous monitoring |
| `--once` | One check and synchronization |
| `--resume` | Reruns a terminal session in place with the same arguments/results |
| `--restart` | Archives a terminal run, then starts a new one with supplied arguments |
| `--stop` | Stops only this session, gracefully then forcibly if needed |
| `--purge-remote` | Final-syncs and deletes only the verified terminal run |

`--restart`, `--resume`, `--stop`, and `--purge-remote` are mutually exclusive.
`--detach` and `--once` are mutually exclusive, and neither is accepted with
`--stop` or `--purge-remote`. Lidar2map arguments are required to create,
resume, or restart a run and must be omitted when reconnecting, stopping, or
purging. Place controller options before the VM target and lidar2map arguments
after `--`.

An unseen host key is accepted on first connection. If OpenSSH reports that a
stored key has changed after a VM rebuild or IP recycling, the controller
automatically removes only that target's stale `known_hosts` entry, accepts the
new key, and retries once. This applies to launch, monitoring, and targeted
stop; the graphical RDP provisioner also renews the target entry itself.

`--reset-host-key` remains available to force that cleanup proactively, before
OpenSSH reports an error:

```bash
lidar2map --remote-cli --reset-host-key --bundle --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --provider fr-ign --zone-city Paris --zone-width 5
```

## Split one area across several VMs

`--block i/M`, passed to lidar2map after `--`, selects geographic block `i` of
`M` non-overlapping blocks. Use an explicit session for every calculation:

```bash
lidar2map --remote-cli --bundle --session var-block-1 root@vm1 -- \
  --lidar --provider fr-ign --laz --zone-department 83 --block 1/3 --download \
  --split-width 5 --cleanup --min-free-gb 20 \
  --shading lrm:sigma=4 --file-formats mbtiles

lidar2map --remote-cli --bundle --session var-block-2 root@vm2 -- \
  --lidar --provider fr-ign --laz --zone-department 83 --block 2/3 --download \
  --split-width 5 --cleanup --min-free-gb 20 \
  --shading lrm:sigma=4 --file-formats mbtiles

lidar2map --remote-cli --bundle --session var-block-3 root@vm3 -- \
  --lidar --provider fr-ign --laz --zone-department 83 --block 3/3 --download \
  --split-width 5 --cleanup --min-free-gb 20 \
  --shading lrm:sigma=4 --file-formats mbtiles
```

Each machine processes its own block and synchronizes below `vm-results/`.
`--block` combines with `--split-width`, so each machine can split its block
again to control disk and memory use. Distinct public IP addresses can also
multiply download throughput when a national portal limits bandwidth per IP.

## RAM and chunk size

For a large `--lidar` area, peak shading memory (especially SVF and openness)
roughly follows the post-split chunk area. The actual causal factor is the
source-tile density in that chunk's VRT, not area alone.

In one département split into a 3×3 grid of roughly 1,150 km² chunks, only the
two chunks whose VRT referenced more than 1,200 LiDAR tiles crashed at about
31 GB RSS on a 32 GB VM. Chunks referencing 100–700 tiles completed. Two
independent crashes reached the same RSS within 23 MB after different numbers
of completed chunks, ruling out a chunk-to-chunk memory leak. Area remains a
useful proxy, but equally sized chunks can differ with LiDAR coverage density.
VAT/e4MSTP, which combines SVF and openness in one pass, tolerates the same
split better. These are empirical targets, not guarantees:

| VM RAM | Target chunk size |
|---|---|
| 32 GB | At most about 600 km²; for example, split a département 4×4 |
| 64 GB | About 1,150 km²; the default 3×3 usually succeeds |

Finer splitting costs time through repeated TMS, VRT, percentile, and seam
passes. It is a trade-off, not a setting to maximize automatically.

The remote controller automatically provisions a dedicated swapfile roughly
equal to VM RAM on launch or reconnection. Swap does not speed up an overly
dense chunk, but turns an OOM kill and loss since the last completed chunk into
a slowdown that can finish. The table remains useful for avoiding that
slowdown.

## Source and standalone development entry points

The integrated modes are recommended. The underlying clients can still be run
from the source checkout for development; they require Python 3.8 or newer:

```bash
python tools/rlidar2map_GUI.py --ip 192.0.2.10
python tools/rlidar2map_CLI.py --bundle --session paris-lrm \
  root@192.0.2.10 -- --lidar --provider fr-ign --zone-city Paris --zone-width 5
```

Dedicated development binaries named `rlidar2map_GUI` and `rlidar2map_CLI`
accept the same options. Replace that prefix with `lidar2map --remote-gui` or
`lidar2map --remote-cli` when using a normal release.

## Build and release architecture

`rlidar2map_CLI.py` and `rlidar2map_GUI.py` are imported by `lidar2map.py`. The
`--remote-cli` / `--remote-gui` dispatch happens before bootstrap and heavy
imports. They are bundled by the same `lidar2map_win.spec` and
`lidar2map_mac.spec` files used for lidar2map; the latter is reused for Linux.

The `.github/workflows/release.yml` matrix therefore builds only one executable
per OS/architecture, and remote execution is included in every
`lidar2map-<os>-<arch>.<zip|tar.gz>` archive.

The dedicated `tools/rlidar2map_CLI.spec` and
`tools/rlidar2map_GUI.spec` remain available for standalone development builds,
but the release workflow no longer invokes them. `lidar2map_icon.png` is
embedded in the Windows and macOS executable and installed on the XFCE desktop
shortcut. Every release page publishes the SHA-256 checksum of each archive.

---

[Documentation index](../README.md#documentation) · [Getting started](getting-started.md)

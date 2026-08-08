# Choosing and understanding LiDAR visualizations

***English** | [Version française](shadings.fr.md)*

The LiDAR point cloud already contains three-dimensional relief: every return
has $(x,y,z)$ coordinates. To map it, lidar2map transforms those points into a
**raster elevation surface**, in which every pixel stores an elevation.
Depending on the workflow, that surface can be a bare-earth digital terrain model (DTM)
interpolated from ground-classified points, a Digital Feature Model (DFM) that
reinjects selected low standing structures, or a surface reconstructed with the
Cloth Simulation Filter (CSF). The [DFM/CSF guide](dfm.md) explains these two
point-cloud methods in detail. On a flat map, elevation alone does not
spontaneously reveal the shape of a bank, the sign of a ditch, or
decimetre-scale microrelief.

lidar2map's “shadings” are therefore, in the broad sense, **2D visual encodings
of the input surface's geometry**. They transform elevation or its relationship
to neighbouring cells — slope and aspect, deviation from broad relief, horizon
angles, visible sky, convexity, and concavity — into luminance or colour. They
neither recreate lost 3D nor alter the source surface: they make its forms
perceptible and select which scales or properties to emphasize. Only hillshade and multidirectional
hillshade actually simulate illumination; LRM, slope, SVF, and openness are
different geometric visualizations.

```mermaid
flowchart LR
    P["3D LiDAR cloud (x, y, z)"] --> S{"Input surface"}
    S --> M["DTM: bare earth"]
    S --> F["DFM: reinjected structures"]
    S --> C["CSF: cloth-filtered surface"]
    M --> Z["Elevation z(x, y)"]
    F --> Z
    C --> Z
    Z --> D["Geometric measure: slope, horizons, scales"]
    D --> I["2D image: luminance or colour"]
```

A 3D viewer can of course display the cloud or any of these surfaces directly,
while contours or hypsometric tints can also encode elevation. Two-dimensional rasters remain
convenient for comparing methods, overlaying other maps, and offline use on a
phone; their local derivatives are particularly effective at detecting subtle
relief beneath forest cover.

Relief visualizations do not all show the same information. A trace that is
strong in a local-relief image can vanish in a hillshade; a bright feature in
positive openness may remain ambiguous until negative openness is inspected.
There is no universal best visualization.

Scale and distance parameters should match the size of the target landforms and
the input surface resolution. For LRM, an explicit `sigma` value is expressed in metres;
its value in pixels is:

$$
\sigma_{px}=\frac{\sigma_m}{\rho}
$$

$\rho$ is the DTM resolution in metres per pixel. A small value emphasizes fine
detail, but also DTM processing noise, modern
features, and edge artefacts. The GUI can add several instances of the same
visualization to compare scales.

## Overview

```mermaid
flowchart LR
    DEM[DTM / DEM] --> D1[Local derivatives]
    DEM --> H[Horizon angles]
    DEM --> F[Scale filters]
    D1 --> HS[Hillshade / multi]
    D1 --> SL[Slope]
    H --> SVF[SVF]
    H --> OP[Openness O+ / O−]
    F --> LRM[Simplified LRM]
    SL --> C[Composites]
    SVF --> C
    OP --> C
    LRM --> C
    C --> VAT[VAT-style]
    C --> RRIM[RRIM-style]
    C --> E4[e4MSTP]
```

| lidar2map output — expanded name | Look for | Strengths | Main limitations |
|---|---|---|---|
| `lrm` — **Local Relief Model**<br>implemented here as **SLRM**, *Simple Local Relief Model* | low walls, narrow ditches, platforms, microrelief | readable, illumination-independent, fast | one scale; removes broad context; small σ amplifies noise and halos |
| `vat` — **Visualization for Archaeological Topography**<br>lidar2map VAT-style variant | general composite reading | pits, mounds and breaks in one image | composite is harder to interpret; slower than LRM |
| `opos` (O+) — **positive openness** | mounds, ridges, banks, upper edges | no illumination direction; excellent for convexities | says little about depressions; strongly radius-dependent |
| `oneg` (O−) — **negative openness** | ditches, hollow ways, pits, lower edges | direct complement to O+ | says little about positive forms; naturally granular |
| `svf` — **Sky-View Factor** | ditches, walls, and features on slopes | little directional bias; retains a useful relief impression | costlier; sensitive to radius, stretch, and flat-ground noise |
| `multi` — **multidirectional hillshade** | familiar overview | fast, intuitive, less biased than one azimuth | still an illumination model; some features remain hidden |
| `315` `045` `135` `225` — **directional hillshades**<br>light-source azimuths | an oriented structure | powerful when light is perpendicular to the trace | strong azimuth bias; always compare directions |
| `slope` — **local terrain slope** | banks, scarps, abrupt breaks | fast and azimuth-independent | no uphill/downhill or mound/pit distinction; noise-sensitive |
| `rrim` — **Red Relief Image Map** | coloured slope plus local relief | combines gradient breaks with local anomalies | lidar2map differs from academic RRIM; colour grammar must be learned |
| `e4mstp` — **e⁴MSTP**<br>**Multiscale Topographic Position — enhanced version 4** | multi-scale exploration of a small area | gathers many clues in one colour image | very expensive; colour grammar takes practice; lidar2map variant differs from the RVT preset |

## Parameters in lidar2map

### Fields shown by the interface

Each click on **+** creates an instance with its own parameters. The same type
can therefore be added twice, for example a local SVF and a broader-context
SVF. Keys in parentheses are those used by the repeatable CLI syntax
`--shading TYPE:key=value,...`.

| Output | Displayed parameters | Initial values | Range proposed by the GUI |
|---|---|---|---|
| `lrm` | smoothing (`sigma`, m) | 15 native pixels, converted to metres | 1–100 m in 0.5 m steps; clear the field to return to auto |
| `vat` | horizon radius (`dist`), final gamma (`gamma`) | 20 m; 2.0 | 10–200 m in 5 m steps; 0.3–3 in 0.1 steps |
| `e4mstp` | horizon radius (`dist`), final gamma (`gamma`) | 20 m; 0.8 | same ranges as VAT |
| `svf` | convention (`conv`), radius (`dist`), gamma (`gamma`), fast calculation (`sweep`) | `flux`; 20 m; 2.0; enabled | `flux` or `rvt`; 10–200 m; 0.3–3; enabled/disabled |
| `opos` | radius (`dist`), gamma (`gamma`) | 20 m; 2.0 | 10–200 m; 0.3–3 |
| `oneg` | radius (`dist`), mirror gamma (`gamma`) | 20 m; 2.0 | 10–200 m; 0.3–3 |
| `rrim` | smoothing (`sigma`, m) | 15 native pixels, converted to metres | 1–100 m in 0.5 m steps; auto when cleared |
| `multi`, `315`, `045`, `135`, `225` | Sun elevation (`elevation`) | 25° | 5–60° in 1° steps |
| `slope` | none | — | — |

These are the **ranges proposed by the interface**, not mathematical limits of
the methods. `dist` and `sigma` are entered in metres and rounded to the nearest
DTM pixel. `gamma`, by contrast, does not change the computed geometry: it only
controls luminance after value stretching.

### LRM and RRIM: `sigma`

`sigma` is the **standard deviation of Gaussian smoothing**, not an exact
object radius. Its automatic value is 15 native pixels: 7.5 m on a
0.5 m/pixel DTM and 15 m on a 1 m/pixel DTM.

- In `lrm`, a small `sigma` retains only very local deviations: fine detail,
  but also noise and small halos. A large `sigma` retains broader structures,
  together with more natural background relief.
- In `rrim`, `sigma` changes only the light/dark SLRM component placed in the
  green and blue channels. The slope-controlled red channel does not change.
- Stretching LRM between its 5th and 95th percentiles makes contrast relative
  to the processed area. Comparing two instances over the same extent is more
  reliable than comparing grey levels from two different projects.

### SVF: `conv`, `dist`, `gamma`, and `sweep`

- `conv=flux` uses the $\cos^2\gamma_k$ convention and is lidar2map's default.
  `conv=rvt` uses $1-\sin\gamma_k$, the **Relief Visualization Toolbox**
  convention. This selects a formula, not a quality level.
- `dist` is the maximum distance over which the horizon is searched in 16
  directions. A small value favours nearby walls and ditches and computes
  faster; a large value includes enclosures, roads, and more distant relief but
  is substantially slower.
- `gamma` is applied after percentile stretching: $I=I_0^\gamma$. Below 1 the
  image becomes lighter; at 1 it remains linear; above 1 midtones become darker.
- Enabled `sweep` selects the accelerated horizon algorithm. It retains the
  same formula and radius but may introduce slight aliasing. Disabling it uses
  the more accurate, slower reference calculation.

### Positive and negative openness: `dist` and `gamma`

Here too, `dist` is the maximum horizon-search radius. A small radius describes
local convexity or concavity; a large one describes broader topographic forms.
It is neither a blur nor the output resolution.

For `opos`, ordinary gamma $I=I_0^\gamma$ follows the SVF rule. For `oneg`,
lidar2map uses **mirror gamma**:

$$
I=1-(1-I_0)^\gamma
$$

Increasing `gamma` for O− therefore pushes the background towards white while
deep depressions remain dark, increasing their visual separation without
darkening the whole image. O+ and O− always use the reference horizon
calculation; `sweep` is not offered for them.

### VAT and e4MSTP: the exact scope of `dist` and `gamma`

- In `vat`, `dist` sets the radius of its internal `flux` SVF and positive
  openness; it does not change slope. Components are blended without gamma,
  then `gamma` is applied once to the final composite. A value above 1 darkens
  it; a value below 1 lightens it.
- In `e4mstp`, `dist` changes only its internal SVF and O+/O− openness layers.
  It changes neither the two fixed SLRMs ($\sigma=1.5$ m and 8 m), nor the
  internal MSTP bands (1.5–5 m, 12–27 m, and 55–100 m), nor slope. `gamma`
  affects only the final colour; its 0.8 default slightly lightens the
  composite.

Increasing `dist` in e4MSTP therefore does not mean “enlarge every scale”. It
only broadens the context of horizon-derived layers.

### Hillshades and slope: `elevation`

For `315`, `045`, `135`, and `225`, the selected type already fixes the light
azimuth. `elevation` is only its height above the horizon:

- low value: grazing light, strong microrelief and directional contrast, with
  more black areas;
- high value: a lighter, gentler image with less pronounced relief;
- 25° is lidar2map's default; 45° suits a more general reading.

`multi` applies the same elevation to four fixed illuminations (225°, 270°,
315°, and 360°), then weights them by slope aspect. Their azimuths are not
adjustable. `slope` has no parameter: it directly encodes local slope from 0 to
90°, independently of Sun position, `dist`, and `gamma`.

### CLI syntax and presets

Each `--shading` occurrence produces one output, and the option is repeatable:

```text
--shading lrm:sigma=10
--shading svf:conv=rvt,dist=20,gamma=1,sweep=0
--shading oneg:dist=100,gamma=2
```

The `--shading-preset` shortcut adds `svf + opos + lrm + multi + slope`:

| Preset | SVF/O+ radius | LRM sigma | Sun | Automatic choice |
|---|---:|---:|---:|---|
| `micro` | 15 m | 8 m | 25° | resolution ≤ 0.75 m/pixel |
| `standard` | 30 m | 15 m | 25° | 0.75 < resolution ≤ 2.5 m/pixel |
| `landscape` | 80 m | 40 m | 30° | resolution > 2.5 m/pixel |

`--shading-preset auto` selects the row from the provider resolution. The
`--shadings tous` keyword deliberately excludes VAT and e4MSTP because these
heavy composites would recalculate layers already requested.

## Historical landmarks

| Year | Method | Contribution |
|---:|---|---|
| 1981 | Horn gradient | robust 3×3 slope/aspect estimate |
| 1992 | Mark multidirectional hillshade | four weighted illuminations reduce orientation bias |
| 2002 | Yokoyama, Shirasawa & Pike openness | illumination-free angular description of convexity and concavity |
| 2008 | Chiba, Kaneta & Suzuki RRIM | red slope plus openness/dominance lightness |
| 2010 | Hesse Local Relief Model | removes broad relief to isolate local landforms |
| 2011 | Zakšek, Oštir & Kokalj SVF | visible-sky fraction applied to relief visualization |
| 2013 | Doneus openness application | joint archaeological reading of convexities and concavities |
| 2018 | Guyot, Hubert-Moy & Lorho MSTP | three topographic-position scales combined as RGB |
| 2019 | Kokalj & Somrak VAT | structured blend of archaeological visualizations |
| 2025 | Kokalj e4MSTP | fusion of MSTP, two SVFs, positive/negative openness, local dominance, and red slope |

e4MSTP was not created by lidar2map. Version 4 is described by [Kokalj
(2025)](https://doi.org/10.1002/arp.70002), has been included in RVT Python
2.2.3 since July 2025, and was further explained by [Kokalj & Čož
(2025)](https://doi.org/10.13140/RG.2.2.19992.66563). The current lidar2map
output is nevertheless a **variant inspired by that method**, not a
pixel-identical implementation of the RVT preset; the differences are detailed
below.

## Slope and hillshade

lidar2map estimates derivatives with Horn's 3×3 operator. For:

```text
a b c
d e f
g h i
```

the gradients are:

$$
p=\frac{(c+2f+i)-(a+2d+g)}{8\,\Delta x},\qquad
q=\frac{(g+2h+i)-(a+2b+c)}{8\,\Delta y}
$$

and slope is:

$$
s=\arctan\!\left(\sqrt{p^2+q^2}\right)
$$

Directional hillshade then applies Lambertian illumination:

$$
I=\max\left(0,
\cos z\cos s+\sin z\sin s\cos(A-\alpha)\right)
$$

where $z$ is solar zenith, $A$ solar azimuth, $s$ slope, and $\alpha$ aspect.
A low light (`elevation=20` to `30`) emphasizes microrelief but increases
contrast; 45° is more neutral for general use. This is local illumination, not
a ray-cast model of true cast shadows.

![Hillshade geometry: Sun, slope, and normal](images/shadings/hillshade-geometry.gif)

*Luminance depends on angle $i$ between the solar ray and the slope normal;
slope, aspect, and Sun position therefore jointly determine intensity. Figure 2
from [Pike
(1992)](https://pubs.usgs.gov/bul/b2016/chapb/ch_b.html), U.S. Geological
Survey, [public
domain](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits).*

### Multidirectional (`multi`)

[Mark (1992)](https://doi.org/10.3133/ofr92422) combines four hillshades.
lidar2map, like GDAL's multidirectional mode, uses azimuths 225°, 270°, 315°,
and 360°:

$$
I_{multi}=\frac{\sum_k w_k I_k}{\sum_k w_k},\qquad
w_k=\sin^2(A_k-\alpha)
$$

This favours illumination perpendicular to the local slope. It is more balanced
than one light source, but it remains an illumination model.

## LRM in lidar2map: the simplified variant

The full LRM published by [Hesse
(2010)](https://doi.org/10.1002/arp.374) builds a purged local elevation model
from zero contours before subtraction. lidar2map uses the faster, common
**Simple Local Relief Model (SLRM)** variant:

$$
R_\sigma(x,y)=z(x,y)-\bigl(G_\sigma*z\bigr)(x,y)
$$

where $G_\sigma*z$ is a Gaussian-smoothed DTM.

```mermaid
flowchart LR
    Z[DTM z] --> B[Gaussian blur Gσ * z]
    Z --> S[Subtract]
    B --> S
    S --> R[Local residual Rσ]
```

![Relief separation into frequency bands](images/shadings/lrm-frequency-principle.png)

*The observed profile is the sum of broad natural relief and higher-frequency
local components. LRM uses this scale separation to isolate small landforms.
Figure 2 from [Toumazet, Simon & Mayoral
(2021)](https://doi.org/10.3390/geomatics1040026), [CC BY
4.0](https://creativecommons.org/licenses/by/4.0/).*

- Small $\sigma$: fine detail and sharp edges, but more noise and halos.
- Large $\sigma$: broader terraces and structures, while fine detail merges
  into the background.
- Gaussian scale is progressive, not an exact maximum object size.

The lidar2map default is 15 native pixels, or 7.5 m for IGN's 0.5 m/pixel
LiDAR. An explicit value below that general-purpose default targets smaller
features; a larger value retains broader structures.

## Sky-View Factor (`svf`)

SVF measures the visible fraction of the sky hemisphere. For horizon angles
$\gamma_k$ sampled along $n$ directions, lidar2map offers two visual
conventions:

$$
SVF_{flux}\approx\frac{1}{n}\sum_{k=1}^{n}\cos^2\gamma_k
$$

and the RVT convention:

$$
SVF_{rvt}\approx\frac{1}{n}\sum_{k=1}^{n}(1-\sin\gamma_k)
$$

![Sky-View Factor principle](images/shadings/sky-view-factor-principle.png)

*In profile (a), relief masks part of the sky hemisphere; in plan view (b), the
horizon is searched along several directions out to radius $R$. Figure 2 from
[Zakšek, Oštir & Kokalj
(2011)](https://doi.org/10.3390/rs3020398), [CC BY
3.0](https://creativecommons.org/licenses/by/3.0/).*

SVF was developed as a relief visualization by [Zakšek, Oštir & Kokalj
(2011)](https://doi.org/10.3390/rs3020398) and applied to archaeological
landscapes by [Kokalj, Zakšek & Oštir
(2011)](https://doi.org/10.1017/S0003598X00067594).

lidar2map uses 16 directions. `dist` limits the horizon search: 20 m targets
microrelief; 100 m may reveal large enclosures and roads, with greater runtime
and a broader spatial context.

## Positive and negative openness

[Yokoyama, Shirasawa & Pike's openness
(2002)](https://www.asprs.org/wp-content/uploads/pers/2002journal/march/2002_mar_257-265.pdf)
summarizes horizon angles over several directions and within a set radius:

$$
\theta_k(r)=\arctan\!\left(\frac{z(p+r u_k)-z(p)}{r}\right)
$$

$$
\beta_k=\max_{r\in(0,L]}\theta_k(r),\qquad
\delta_k=\min_{r\in(0,L]}\theta_k(r)
$$

$$
O^+=\frac{1}{n}\sum_k\left(\frac{\pi}{2}-\beta_k\right),\qquad
O^-=\frac{1}{n}\sum_k\left(\frac{\pi}{2}+\delta_k\right)
$$

$L$ is the analysis radius and $u_k$ a direction. **O− is not merely the
inverse of O+.** They describe complementary geometry.

![Positive and negative openness principle](images/shadings/openness-principle.png)

*Red zenith angles define O+; white nadir angles define O−. The calculation is
repeated in every direction out to radius $r$. Figure 1 from [Doneus
(2013)](https://doi.org/10.3390/rs5126427), [CC BY
3.0](https://creativecommons.org/licenses/by/3.0/).*

lidar2map displays `oneg` inverted so depressions are dark. O+ and O− are best
read side by side. Both outputs are percentile-stretched per dataset, so their
display values are visual contrasts, not directly comparable physical angles
between projects.

## RRIM: publication and lidar2map variant

The original RRIM by [Chiba, Kaneta & Suzuki
(2008)](https://isprs.org/proceedings/XXXVII/congress/2_pdf/11_ThS-6/08.pdf)
maps slope to red chroma and dominance to lightness, using an openness-derived
quantity:

$$
D=\frac{O^+-O^-}{2}
$$

![Geometric encoding used by RRIM](images/shadings/rrim-colour-principle.png)

*In published RRIM, the vertical axis controls red chroma through slope; the
horizontal $D$ axis separates convexity from concavity and controls lightness.
Cropped from Figure 7 in [Chiba, Kaneta & Suzuki
(2008)](https://isprs.org/proceedings/XXXVII/congress/2_pdf/11_ThS-6/08.pdf),
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).*

lidar2map's `rrim` is an **RRIM-style composite**, not an exact reproduction:

$$
R=255\left[\min\left(1,\max\left(0,\frac{s}{45^\circ}\right)\right)\right]^{0.7}
$$

$$
G=B=255\,N_{5,95}(R_\sigma)^{0.8}
$$

$N_{5,95}$ stretches the simplified LRM residual between its 5th and 95th
percentiles. This variant combines red slope and light/dark local relief; it is
not a quantitative dominance map in the 2008 sense.

## VAT and e4MSTP

VAT as published by [Kokalj & Somrak
(2019)](https://doi.org/10.3390/rs11070747) combines hillshade, inverted slope,
positive openness, and SVF with defined stretches and blend modes.

![Workflow of the published VAT](images/shadings/vat-workflow.png)

*Published VAT workflow: compute and normalize the layers, then blend them in a
defined order and at defined opacities. Figure 1 from [Kokalj & Somrak
(2019)](https://doi.org/10.3390/rs11070747), [CC BY
4.0](https://creativecommons.org/licenses/by/4.0/). The lidar2map variant below
is not this exact preset.*

lidar2map's `vat` is **VAT-style**. SVF is the base, a positive-openness overlay
enhances convexity, and slope darkens scarps. With the current internal 0.5
opacities:

$$
V=\left[0.5S+0.5B(S,O^+)\right]\left(1-0.5P\right)
$$

$B$ is the Overlay blend: for $S\leq 0.5$, $B(S,O^+)=2SO^+$; above that value,
$B(S,O^+)=1-2(1-S)(1-O^+)$. The selected gamma is then applied. $S$ is
normalized SVF and $P$ normalized slope. It is therefore not pixel-identical to
the RVT VAT preset.

### Published e4MSTP

The e⁴MSTP published by [Kokalj
(2025)](https://doi.org/10.1002/arp.70002) is a complex blend designed for
multi-scale detection; “e⁴” means *enhanced version 4*. The [reference RVT
recipe](https://rvt-py.readthedocs.io/en/latest/rvt.blend.html#rvt.blend.e4mstp)
stacks the layers in this order:

```mermaid
flowchart LR
    S["Red slope (0–55°)"] --> OL["× O+ − O− and local dominance"]
    OP["O+ − O−"] --> OL
    LD["Local dominance"] --> OL
    OL --> SV["× two merged SVFs"]
    SV1["General-terrain SVF"] --> SV
    SV2["Flat-terrain SVF, 10 m radius"] --> SV
    SV --> M["MSTP Overlay at 90%"]
    MSTP["MSTP"] --> M
    M --> E4["e⁴MSTP"]
```

- the O+ − O− difference, stretched from −15 to 15, is placed at 50% over
  local dominance stretched from 0.5 to 1.8;
- a general-terrain SVF stretched from 0.7 to 1 is merged with a second SVF
  for flat terrain, computed with a 10 m radius and stretched from 0.9 to 1;
  the combined layer is multiplied at 25%;
- MSTP is finally added in Overlay mode at 90%.

This version is particularly effective at showing subtle topographic variation
in very flat terrain and small structures. Its colours take time to learn and
are better suited to detection and recognition than detailed interpretation.
A Luminosity blend can remove the colours when they distract from the forms.

### Current lidar2map variant

lidar2map's `e4mstp` output combines its MSTP calculation, one SVF, O+, O−,
slope, and two SLRM residuals ($\sigma=1.5$ m and 8 m). It does not calculate
local dominance, does not merge the two SVFs from the reference recipe, and
uses a Gaussian approximation of MSTP with different scales and RGB encoding
from RVT. The stretches, opacities, and blend modes also differ. It is therefore
an **experimental e4MSTP-inspired variant**, not a pixel-identical reproduction
of the RVT preset.

Its standardized topographic deviation at each scale is based on:

$$
DEV_\sigma=\frac{z-G_\sigma(z)}
{\sqrt{\max(G_\sigma(z^2)-G_\sigma(z)^2,0)}+10^{-3}}
$$

It can be information-rich on a small site, but its many Gaussian scales and
horizon layers make it unsuitable as a first view or a cheap department-wide
render.

```mermaid
flowchart LR
    Z[DTM z] --> L[Local topographic position]
    Z --> M[Intermediate topographic position]
    Z --> B[Broad topographic position]
    L --> RGB[One colour channel per scale band]
    M --> RGB
    B --> RGB
    RGB --> MSTP[MSTP composition]
```

*MSTP geometry in principle: measure a point's relative position in its
neighbourhood at three scales, then combine the three measurements as colour.
Exact channel assignment and scales depend on the implementation; e4MSTP then
adds the layers shown in the preceding workflow.*

## Cross-reading and validation

1. **Scale:** compare several LRM values, from fine detail to broader forms.
2. **Feature sign:** read O+ and O− side by side to distinguish convexities from
   concavities.
3. **Context:** use SVF, VAT, or RRIM to place an anomaly in the surrounding
   relief.
4. **Orientation:** compare several hillshade azimuths when geometry remains
   ambiguous.
5. **Return to evidence:** check aerial imagery, cadastral and historical maps,
   and the ground. A visualization is never archaeological proof.

DTM artefacts can mimic archaeology: tile edges, vegetation interpolation,
removed buildings, modern drains, forestry tracks, point-cloud noise, or survey
campaign boundaries. A credible feature should survive several independent
visualizations and retain coherent geometry.

## References

- Horn, 1981 — [*Hill Shading and the Reflectance Map*](https://doi.org/10.1109/PROC.1981.11918).
- Pike, 1992 — [*Machine Visualization of Synoptic Topography by Digital Image Processing*](https://pubs.usgs.gov/bul/b2016/chapb/ch_b.html).
- Mark, 1992 — [*A multidirectional, oblique-weighted, shaded-relief image of the Island of Hawaii*](https://doi.org/10.3133/ofr92422).
- Yokoyama, Shirasawa & Pike, 2002 — [*Visualizing Topography by Openness*](https://www.asprs.org/wp-content/uploads/pers/2002journal/march/2002_mar_257-265.pdf).
- Chiba, Kaneta & Suzuki, 2008 — [*Red Relief Image Map*](https://isprs.org/proceedings/XXXVII/congress/2_pdf/11_ThS-6/08.pdf).
- Hesse, 2010 — [*LiDAR-derived Local Relief Models*](https://doi.org/10.1002/arp.374).
- Toumazet, Simon & Mayoral, 2021 — [*Self-AdaptIve LOcal Relief Enhancer (SAILORE)*](https://doi.org/10.3390/geomatics1040026).
- Zakšek, Oštir & Kokalj, 2011 — [*Sky-View Factor as a Relief Visualization Technique*](https://doi.org/10.3390/rs3020398).
- Kokalj, Zakšek & Oštir, 2011 — [archaeological SVF application](https://doi.org/10.1017/S0003598X00067594).
- Doneus, 2013 — [*Openness as Visualization Technique for Interpretative Mapping*](https://doi.org/10.3390/rs5126427).
- Kokalj & Hesse, 2017 — [*Airborne Laser Scanning Raster Data Visualization*](https://doi.org/10.3986/9789612549848).
- Guyot, Hubert-Moy & Lorho, 2018 — [multi-scale MSTP approach](https://doi.org/10.3390/rs10020225).
- Kokalj & Somrak, 2019 — [*Why Not a Single Image?* — VAT](https://doi.org/10.3390/rs11070747).
- Kokalj, 2025 — [*Standardizing Visualization in Ancient Maya Lidar Research*](https://doi.org/10.1002/arp.70002).
- Kokalj & Čož, 2025 — [*Advancement of Relief Interpretation with a Complex Combination of Visualisation Techniques*](https://doi.org/10.13140/RG.2.2.19992.66563).
- Relief Visualization Toolbox — [eMSTP documentation](https://rvt-py.readthedocs.io/en/latest/listofvis_emstp.html) and [e4MSTP recipe](https://rvt-py.readthedocs.io/en/latest/rvt.blend.html#rvt.blend.e4mstp).

Original files and figure licences are listed in the [illustration
registry](images/shadings/README.md).

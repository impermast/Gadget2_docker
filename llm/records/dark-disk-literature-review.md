# Literature review: dissipative DM and dark-disk formation

**Why/when to use:** constrain claims about dark-disk formation and parameter applicability; consult before comparing our phenomenological all-DM `f_diss` runs with cosmological/subcomponent cooling models. Not a current experiment plan.

Date: 2026-10-13. Scope restricted to arXiv records and peer-reviewed journal
articles. Blog posts, popular summaries, repositories, and software documentation
were not used as physical evidence.

## Article-by-article findings

| Paper | Model and parameters | Main result relevant here | Applicability to our runs |
|---|---|---|---|
| Shen et al. 2021, “Dissipative dark matter on FIRE – I” ([arXiv:2102.09580](https://arxiv.org/abs/2102.09580); [MNRAS 506, 4421–4445](https://academic.oup.com/mnras/article/506/3/4421/6324018), DOI [10.1093/mnras/stab2042](https://doi.org/10.1093/mnras/stab2042)) | Cosmological FIRE-2 dwarf zoom-ins evolved to z=0; varied cosmological halos rather than a controlled initial-spin sweep. Main dwarf sample is roughly `10^10–10^11 Msun`; the ultra-faint m09 counterpart is `2.5e9 Msun`. Literature `f_diss` is the fraction of pair-relative kinetic energy lost per collision. Fiducial `f_diss=0.5`; constant `sigma/m=0.1,1,10 cm^2/g`, plus a velocity-dependent model. One m09 test compares `(f_diss,sigma/m)=(0.1,5),(0.5,1),(0.9,0.56)`. Approximate FIRE dwarf resolution: baryonic particle masses 250–2000 Msun, DM particles about 5x heavier, DM force resolution 40 pc, gas softening about 0.5–2 pc. | At the largest cross-sections, some dwarfs develop substantial coherent DM rotation and oblate shapes; the authors explicitly distinguish this from a thin, well-defined dark disk. Response depends on galaxy and radius. Dissipation is not characterized by `f_diss` alone; interaction/dissipation timescale and collisional energy transfer matter. | Closest direct literature model to our constant-cross-section dSIDM, but it is a cosmological, baryonic FIRE setup rather than our isolated, single-component, pre-rotating NFW halo. It has no single matched Bullock-spin value or direct prediction for our `f_diss=0.5, sigma/m=1–2` points. |
| Shen et al. 2024, “Dissipative dark matter on FIRE – II” ([arXiv:2206.05327](https://arxiv.org/abs/2206.05327); [ApJ 966, 131](https://doi.org/10.3847/1538-4357/ad2fb1)) | Uses the FIRE dSIDM dwarf suite and compares with isolated bright-dwarf H I rotation curves. The m09 ultra-faint model has CDM-counterpart `M_vir=2.5e9 Msun` and a quoted DM-only convergence radius of 65 pc; this is not the force softening. Parameter tests include `(f_diss,sigma/m)=(0.5,1),(0.1,5),(0.9,0.56)` for m09. | Derives an approximate constraint `f_diss * (sigma/m) <= 0.05 cm^2/g` for the constant-cross-section models considered; for `f_diss=0.5`, this corresponds to `sigma/m` around or below 0.1 cm^2/g for that bright-dwarf population. At m09, low `f_diss=0.1` can drive a denser center/gravothermal evolution; the m09 parameter tests focus on density profiles, not a disk-formation time. Constraints are weaker for other dwarf populations and velocity-dependent models. | This is a phenomenological constraint in a particular baryonic dwarf-galaxy context, not a dark-disk formation threshold and not a direct exclusion of our DM-only numerical experiment. It means `f_diss=0.5, sigma/m=1–2` should be labelled an exploratory/high-interaction test, not automatically a preferred viable dwarf model. |
| Fan et al. 2013, “A Dark-Disk Universe” ([arXiv:1303.3271](https://arxiv.org/abs/1303.3271); [PRL 110, 211302](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.110.211302), DOI [10.1103/PhysRevLett.110.211302](https://doi.org/10.1103/PhysRevLett.110.211302)) | Analytical/theoretical Double-Disk Dark Matter proposal, not a resolved galaxy simulation. The dissipative component is subdominant; the paper estimates a thin disk could contain up to about 5% of MW DM under its surface-density assumptions. Illustrative dark-atomic parameters include `m_C~1 MeV`, `m_X~1–100 GeV`, and `alpha_D`; its fiducial disk-height estimate is about 2.5 pc for `alpha_D=0.02, m_C=1 MeV, m_X=100 GeV`. Cooling is compared with a Hubble-time scale in an illustrative z~2 setup; no N-body resolution, softening, or prescribed halo spin is supplied. | Cooling removes energy while angular momentum and tidal torques permit the component to settle into a rotationally supported disk. The result is a minority dark component, not the whole collisionally interacting NFW halo. It does not prescribe our GIZMO `DM_DissipationFactor` or a universal constant `f_diss`/`sigma/m` threshold. | Conceptually relevant to “dark disk”, but not a parameter-matched prediction for our single-component runs. |
| Rosenberg & Fan 2017, “Cooling in a Dissipative Dark Sector” ([arXiv:1705.10341](https://arxiv.org/abs/1705.10341); [PRD 96, 123001](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.96.123001), DOI [10.1103/PhysRevD.96.123001](https://doi.org/10.1103/PhysRevD.96.123001)) | Microphysical cooling model for an atomic dark plasma with dark-electron/proton masses, dark fine-structure coupling `alpha_D`, temperature, and dissipative-component fraction as inputs. Includes dark-photon Compton scattering, bremsstrahlung, recombination, and collisional processes. An illustrative estimate uses a 1% dissipative fraction; it is not a simulated disk threshold. No galaxy IC, particle resolution, softening, or formation time is supplied. | Supplies cooling prescriptions and shows why disk formation depends on dark-sector particle masses, coupling, temperature, density, and cooling time—not on a single elastic-scattering energy-loss fraction. It does not establish one universal disk-forming parameter point. | Helps distinguish true radiative cooling/subcomponent disk models from our phenomenological per-collision dSIDM kick. |
| Roy et al. 2023, “Simulating Atomic Dark Matter in Milky Way Analogues” ([arXiv:2304.09878](https://arxiv.org/abs/2304.09878); [ApJL 954, L40](https://doi.org/10.3847/2041-8213/ace2c8)) | Cosmological m12i Milky-Way zoom-in, `M_halo~1e12 Msun`, with 6% of total DM in ADM and two atomic-cooling benchmarks; no spin-matched IC sweep. Particle masses: CDM `2.62e5 Msun`, ADM `1.67e4 Msun`, baryons `5.6e4 Msun`; CDM force resolution 40 pc and minimum gas softening 1.4 pc. | ADM gas disks settle by about z~2, are later disturbed by mergers/inflows around z~1, and much of the inner ADM is in clumps by z=0 (about 95% in the reported inner region). The disk-like component is aligned with the baryonic disk. | Strong dark-disk example, but the 6% atomic component and explicit dark-sector cooling microphysics are fundamentally different from applying a constant `f_diss` to all DM particles. Do not translate its atomic parameters into our `f_diss`. |

## Match to the present experiment

Our matched experiment uses one isolated spherical NFW halo with `N=10^6`
particles, imposed Bullock spin `lambda'_200=0.035`, and no baryonic component;
its GIZMO `SofteningHalo=0.05` is in the project's runtime units. It is evolved
for `TimeMax=1` code-time unit, not through a cosmological history. The new
`f_diss=0.5` points therefore match the FIRE m09 scalar pair `(0.5,1)` only at
the phenomenological parameter level. They do not match the FIRE initial
conditions, baryonic physics, halo assembly, resolution, or subcomponent
fraction. For `sigma/m=1,2`, the product `f_diss*(sigma/m)` is 0.5 and
1 cm^2/g respectively—about 10 and 20 times the approximate bright-dwarf FIRE-II
bound quoted above. This ratio is a context flag, not a direct exclusion of our
DM-only experiment.

## Convention crosswalk and conclusions

- In the literature above, `f_diss` denotes an energy-loss fraction. Our unchanged
  legacy executable uses `v_rel'=(1-D_code)*v_rel`; therefore the input mapping is
  `D_code=1-sqrt(1-f_diss)`. For `f_diss=0.5`, pass `D_code=0.2928932188`.
- The article record does **not** support a universal rule that `f_diss<0.5` is
  required for either numerical stability or dark-disk formation. FIRE I shows
  rotation/oblateness at high `sigma/m` but not a thin disk; DDDM/ADM thin disks
  rely on subcomponent fractions and cooling physics absent from our model.
- Our current `sigma/m=1,2`, `f_diss=0.5` batch is useful as an explicitly
  exploratory mechanism test. The FIRE-II bright-dwarf constraint cautions that
  this constant-cross-section combination is not automatically a viable
  phenomenological model for isolated bright dwarfs.
- In our own lower-`f_diss` runs, none met the combined shape/thickness/rotation
  disk criteria. Literature therefore motivates measuring angular-momentum
  retention, cooling/dissipation timescale, shape, and rotation jointly—not
  choosing `f_diss` alone.

## Sources

1. [Shen et al. 2021, arXiv:2102.09580](https://arxiv.org/abs/2102.09580); [MNRAS article](https://academic.oup.com/mnras/article/506/3/4421/6324018).
2. [Shen et al. 2024, arXiv:2206.05327](https://arxiv.org/abs/2206.05327); [ApJ article](https://doi.org/10.3847/1538-4357/ad2fb1).
3. [Fan et al. 2013, arXiv:1303.3271](https://arxiv.org/abs/1303.3271); [PRL article](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.110.211302).
4. [Rosenberg & Fan 2017, arXiv:1705.10341](https://arxiv.org/abs/1705.10341); [PRD article](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.96.123001).
5. [Roy et al. 2023, arXiv:2304.09878](https://arxiv.org/abs/2304.09878); [ApJL article](https://doi.org/10.3847/2041-8213/ace2c8).

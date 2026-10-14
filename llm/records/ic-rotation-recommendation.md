# Rotating NFW IC: literature basis and prepared variant

**Why/when to use:** establish provenance, measurement conventions, and known quality limitations before using the prepared rotating N=1e6 IC; this is not evidence of simulated stability or permission to launch.

**Disposition:** a new rotated IC was prepared from an existing 1e6-particle NFW halo. No GIZMO simulation was launched.

## Selected initial condition

- Source IC: `nbody/ics/dwarf_N1e6/dwarf_N1e6.hdf5`.
- Source GalIC model: `N=1,000,000`, `CC=15`, `V200=30 km/s`, spherical halo, no disk/bulge, `TypeOfHaloVelocityStructure=0`, zero input streaming. Its recorded NFW fit has `r_s=1.4415 kpc`; the existing IC gate reports acceptable NFW/cusp profile checks, but **fails its separate central-resolution threshold** (`N(<1 kpc)=41,929` vs the gate's requested `100,000`).
- Output IC: `nbody/ics/dwarf_rot_N1e6_lambda0035/dwarf_rot_N1e6_lambda0035.hdf5`.
- The output is a copy of the source with only a seeded sign-bias of `v_phi` for retrograde particles. All positions, masses, particle IDs, particle count and hence the realized spatial/NFW profile are exactly unchanged. No particles are cut at an outer radius.
- Bullock target: `lambda'_200=0.035`, aligned with `+z`; this is the previously agreed fiducial and is close to the cosmological halo-spin median reported by Bullock et al. (2001). It is a representative spin, not a claim that spin alone guarantees a disk.
- The operational SO-200 aperture used for this realization is `R200=27.51515 kpc`, derived from the actual 1e6-particle mass profile with provisional project convention `H0=0.1 km/s/kpc`. Inside it: `M200=0.48436766` code mass (`4.84368e9 Msun`) and `V200=27.51514 km/s`. The source's nominal GalIC labels are retained and unchanged (`V200=30 km/s`); the measured aperture convention is recorded explicitly rather than silently equating nominal and realized R200.
- Initial measured `lambda'_200=0.00011186`; output measured `lambda'_200=0.03501867`. `192,158` of `499,505` whole-halo retrograde candidates were flipped (`148,271` currently inside and `43,887` outside the measurement aperture). The outside particles are retained and get the same phase-independent random-thinning treatment.
- In the source bulk frame the largest stored-file squared-speed discrepancy for flipped particles is `8.59e-4 (km/s)^2`, relative `1.18e-7`; this is float32 HDF5 rounding. The in-memory flip preserves speed to floating-point precision.
- Source SHA-256: `c016e820b1fc8492556e0d3eb5302f0a614a21315fe25a1be75f741b33d7027f`.
- Output SHA-256: `308599c843f887a574b5c0773591d906d6c80c4c15da4bec85fb9489d84b1c0a`.
- Machine-readable provenance: `nbody/ics/dwarf_rot_N1e6_lambda0035/spin_bias_manifest.json`.

## Physical rationale and limits of the literature

1. **Use a typical, interpretable halo spin first.** Bullock et al. (2001), *A Universal Halo Spin Profile and the Mass and Angular Momentum Distribution in Galactic Halos*, find a characteristic median Bullock spin `lambda' ~ 0.035`. This supports the agreed fiducial as a cosmologically representative starting point. It does **not** assert that a halo at this spin must make a disk.
2. **A rotating NFW halo is not already a disk.** NFW constrains the initial spatial density. The sign-bias changes the odd-in-`Lz` part of the velocity distribution, leaving the spherical density and even velocity moments unchanged at `t=0`. Dissipation must subsequently remove energy while sufficient angular momentum remains in the collapsing material for a flattened, rotation-supported component to develop.
3. **High spin is not a proven disk switch.** Xiao et al. (2021), *SMBH Seeds from Dissipative Dark Matter* (arXiv:2103.13407), compare isolated NFW halo collapse at Peebles-spin `lambda=0.03` and `0.1`. Their high-spin case still collapses on a similar timescale; their subject is central collapse/seed formation, not a demonstrated thin dark disk. Their Peebles `lambda` values must not be equated numerically to Bullock `lambda'` without conversion.
4. **Strong dSIDM can create rotation without a thin disk.** Shen et al. (2021), *Dissipative Dark Matter on FIRE I* (arXiv:2102.09580), find coherent inner-halo rotation and oblate shapes in some high-interaction cases, but not a universal thin, well-defined dark disk. Thus the later GIZMO `sigma/m` and dissipation parameter `D` are essential; the IC alone cannot guarantee the desired morphology.
5. **Atomic dark-disk models are related but different.** Roy et al. (2023), *Simulating Atomic Dark Matter in Milky Way Analogues* (arXiv:2304.09878), form a disk from a subdominant dissipative atomic-dark-matter component in cosmological simulations. That is not the same model as making the entire single-component halo in this project dissipative.

### Recommendation for the next simulation-design stage

Use this `lambda'=0.035` IC as the fiducial. If the scientific priority later becomes maximizing rotational flattening rather than representing a typical halo, add a separate high-spin control with the **same NFW profile and mass**, but define its spin convention consistently and treat it as an exploratory comparison. Do not claim a thin disk based only on initial spin. Compare the CDM stability control and dSIDM run using shape (`c/a`), `V_rot/sigma`, disk-plane alignment, angular-momentum profiles, and radial density evolution.

## References

- Bullock, J. S., Dekel, A., Kolatt, T. S., et al. (2001), “A Universal Halo Spin Profile and the Mass and Angular Momentum Distribution in Galactic Halos,” *ApJ* 555, 240. [arXiv:astro-ph/0011001](https://arxiv.org/abs/astro-ph/0011001).
- Xiao, H., Shen, X., Hopkins, P. F., & Zurek, K. M. (2021), “SMBH Seeds from Dissipative Dark Matter,” *JCAP* 07, 039. [arXiv:2103.13407](https://arxiv.org/abs/2103.13407).
- Shen, X., Hopkins, P. F., Necib, L., et al. (2021), “Dissipative dark matter on FIRE – I. Structural and kinematic properties of dwarf galaxies,” *MNRAS* 506, 4421. [arXiv:2102.09580](https://arxiv.org/abs/2102.09580).
- Roy, S., Shen, X., Lisanti, M., et al. (2023), “Simulating Atomic Dark Matter in Milky Way Analogues,” [arXiv:2304.09878](https://arxiv.org/abs/2304.09878).
- Huo, R., Yu, H.-B., & Zhong, Y.-M. (2019), “The Structure of Dissipative Dark Matter Halos,” [arXiv:1912.06757](https://arxiv.org/abs/1912.06757).

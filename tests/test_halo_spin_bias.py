import h5py
import numpy as np
import pytest

from halo_spin_bias import (
    _flip_candidates,
    apply_spin_bias,
    angular_momentum,
    bullock_lambda_prime,
    halo_frame,
    transform_ic,
)


def retrograde_fixture():
    angles = np.arange(4) * (np.pi / 2)
    pos = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(4)))
    # v_phi=-1 at every particle; equal-mass, centered, circular-orbit fixture.
    vel = np.column_stack((np.sin(angles), -np.cos(angles), np.zeros(4)))
    mass = np.ones(4)
    return pos, vel, mass


def test_spin_bias_flips_retrograde_vphi_and_hits_discrete_target():
    pos, vel, mass = retrograde_fixture()
    new_vel, report = apply_spin_bias(pos, vel, mass, r200=2.0,
                                      target_lambda_prime=0.125, seed=7,
                                      grav_const=1.0)

    assert report["particles_flipped"] == 3
    assert report["lambda_prime_initial"] == pytest.approx(0.25)
    assert report["lambda_prime_final"] == pytest.approx(0.125)
    assert report["j_initial"][2] == pytest.approx(-4.0)
    assert report["j_final"][2] == pytest.approx(2.0)
    np.testing.assert_allclose(np.linalg.norm(new_vel, axis=1),
                               np.linalg.norm(vel, axis=1))
    np.testing.assert_array_equal(pos, retrograde_fixture()[0])


def test_spin_bias_is_reproducible_and_preserves_unselected_particles():
    pos, vel, mass = retrograde_fixture()
    a, ra = apply_spin_bias(pos, vel, mass, 2.0, 0.125, seed=29, grav_const=1.0)
    b, rb = apply_spin_bias(pos, vel, mass, 2.0, 0.125, seed=29, grav_const=1.0)
    np.testing.assert_array_equal(a, b)
    assert ra["particles_flipped"] == rb["particles_flipped"]
    assert ra["flipped_speed_squared_max_abs_error"] < 1e-14
    changed = np.any(a != vel, axis=1)
    assert np.count_nonzero(changed) == 3
    # z=0 makes the azimuthal flip leave the other angular momentum components zero.
    assert abs(ra["j_final"][0]) < 1e-14
    assert abs(ra["j_final"][1]) < 1e-14


def test_flip_candidates_include_retrograde_particles_outside_r200():
    dx = np.array([[1., 0., 0.], [0., 1., 0.], [-1., 0., 0.],
                   [0., -1., 0.], [3., 0., 0.]])
    dv = np.array([[0., -1., 0.], [1., 0., 0.], [0., 1., 0.],
                   [-1., 0., 0.], [0., -1., 0.]])
    masses = np.ones(5)
    inside = np.linalg.norm(dx, axis=1) <= 1.5
    candidates, delta_j, delta_p = _flip_candidates(dx, dv, masses, inside)
    assert len(candidates) == 5  # radius must not be part of the flip selection
    assert candidates[-1] == 4
    np.testing.assert_array_equal(delta_j[-1], np.zeros(3))  # but outside R200 adds no initial aperture J
    assert np.linalg.norm(delta_p[-1]) > 0


def test_spin_bias_rejects_unreachable_target():
    pos, vel, mass = retrograde_fixture()
    prograde = vel.copy()
    prograde[:, :2] *= -1
    with pytest.raises(ValueError, match="already exceeds"):
        apply_spin_bias(pos, prograde, mass, 2.0, 0.125, seed=1, grav_const=1.0)


def test_halo_frame_shrinking_center_rejects_a_distant_outlier():
    pos = np.zeros((1001, 3), dtype=float)
    pos[-1, 0] = 10_000.0
    vel = np.zeros_like(pos)
    vel[-1, 1] = 10.0
    center, bulk = halo_frame(pos, vel, np.ones(len(pos)))
    np.testing.assert_allclose(center, np.zeros(3), atol=1e-12)
    assert bulk[1] == pytest.approx(10.0 / 1001.0)


def test_bullock_lambda_uses_angular_momentum_magnitude():
    lam, v200 = bullock_lambda_prime(4.0, np.array([0.0, 0.0, 4.0]), 2.0, 1.0)
    assert v200 == pytest.approx(np.sqrt(2.0))
    assert lam == pytest.approx(0.25)


def test_transform_writes_new_file_and_records_provenance(tmp_path):
    pos, vel, mass = retrograde_fixture()
    source = tmp_path / "input.hdf5"
    output = tmp_path / "new" / "output.hdf5"
    with h5py.File(source, "w") as f:
        header = f.create_group("Header")
        header.attrs["MassTable"] = np.zeros(6)
        group = f.create_group("PartType3")
        group.create_dataset("Coordinates", data=pos.astype(np.float32))
        group.create_dataset("Velocities", data=vel.astype(np.float32))
        group.create_dataset("Masses", data=mass.astype(np.float32))
        group.create_dataset("ParticleIDs", data=np.arange(len(mass), dtype=np.uint32))
    before = source.read_bytes()

    report = transform_ic(source, output, 3, 2.0, 0.125, 11, 1.0)

    assert source.read_bytes() == before
    assert report["lambda_prime_final"] == pytest.approx(0.125)
    with h5py.File(output, "r") as f:
        assert f["PartType3/Velocities"].shape == (4, 3)
        np.testing.assert_array_equal(f["PartType3/ParticleIDs"], np.arange(4, dtype=np.uint32))
        assert f["Header"].attrs["HaloSpinBiasMethod"] == "retrograde_vphi_sign_flip_v1"
        assert f["Header"].attrs["HaloSpinBiasSeed"] == 11
        assert f["Header"].attrs["HaloSpinBiasTargetBullockLambdaPrime"] == pytest.approx(0.125)

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        transform_ic(source, output, 3, 2.0, 0.125, 11, 1.0)


def test_angular_momentum_rejects_empty_r200():
    pos, vel, mass = retrograde_fixture()
    with pytest.raises(ValueError, match="no particles"):
        angular_momentum(pos, vel, mass, np.zeros(3), np.zeros(3), r200=0.1)

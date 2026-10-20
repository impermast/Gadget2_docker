from pathlib import Path


def test_make_plots_skill_copies_stay_synchronized():
    """Agent entrypoint and workflow docs have one canonical content copy."""
    repo = Path(__file__).resolve().parent.parent
    canonical = repo / ".agents/skills/make-plots"
    cline = repo / ".cline/skills/make-plots"

    canonical_files = {
        path.relative_to(canonical): path.read_bytes()
        for path in canonical.rglob("*") if path.is_file()
    }
    cline_files = {
        path.relative_to(cline): path.read_bytes()
        for path in cline.rglob("*") if path.is_file()
    }
    assert cline_files == canonical_files, (
        "Update .cline/skills/make-plots to match .agents/skills/make-plots"
    )

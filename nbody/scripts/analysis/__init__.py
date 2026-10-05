"""Единая точка входа пакета analysis: реестр + пути + loaders."""
from .loaders import *  # noqa: F401,F403 (публичное API loaders)
from .paths import AnalysisPaths, BLOCK_NAMES, default_analysis_root  # noqa: F401
from .registry import (  # noqa: F401
    BLOCK_INPUTS,
    BLOCK_RUNNERS,
    BLOCK_TITLES,
    BLOCKS,
    PlotSpec,
    RegistryError,
    by_block,
    describe,
    find,
    register,
    registry,
    reset_for_tests,
    to_markdown,
    validate_registry,
)

__all__ = ["AnalysisPaths", "BLOCKS", "BLOCK_NAMES", "BLOCK_TITLES",
           "BLOCK_INPUTS", "BLOCK_RUNNERS", "PlotSpec", "RegistryError",
           "by_block", "describe", "find", "register", "registry",
           "reset_for_tests", "to_markdown", "validate_registry",
           "default_analysis_root"]

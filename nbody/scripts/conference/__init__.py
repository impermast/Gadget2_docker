"""Small, non-rendering helpers for the conference evidence package.

The conference tools deliberately stay separate from the plotting stack.  They
only inventory run directories and consume the text/CSV diagnostics produced by
the existing ``check_simulations`` tools.
"""

__all__ = ["manifest"]

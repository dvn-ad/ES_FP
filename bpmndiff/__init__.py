"""bpmndiff: a pure-Python BPMN/XPDL comparison prototype.

Pipeline: parse & normalise -> tiered alignment -> SESE decomposition ->
relabelling -> per-fragment LTS equivalence -> edit script & fusion report.
"""

__version__ = "0.1.0"

from .diff import Comparison, DiffOptions, diff_models  # noqa: F401
from .model import Edge, Node, ProcessModel  # noqa: F401
from .parsers import ParseError, load_model  # noqa: F401

__all__ = [
    "__version__",
    "Comparison",
    "DiffOptions",
    "diff_models",
    "Edge",
    "Node",
    "ProcessModel",
    "ParseError",
    "load_model",
]

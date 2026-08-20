"""Public RealSynthEngine v4 stateful core API.

Implementation is split by responsibility; offline and interactive paths share
the same RealSynthEngineV4 block state machine. No audition or A5 logic lives here.
"""
from .real_synth_v4_model import *
from .real_synth_v4_engine import RealSynthEngineV4
from .real_synth_v4_host import *

# Re-export the frozen public surface used by Gate A/B.

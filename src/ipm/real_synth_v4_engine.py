from __future__ import annotations
from .real_synth_v4_lifecycle_base import _LifecycleBaseMixin
from .real_synth_v4_lifecycle_start import _LifecycleStartMixin
from .real_synth_v4_dsp import _VoiceDSPMixin
from .real_synth_v4_process import _ProcessMixin

class RealSynthEngineV4(_LifecycleBaseMixin, _LifecycleStartMixin, _VoiceDSPMixin, _ProcessMixin):
    pass

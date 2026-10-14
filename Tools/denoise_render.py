"""Compatibility entry point for the provenance-preserving source denoiser.
Prefer Source/denoise_preview.py. Both entry points use the same guide-aware
implementation and refuse double filtering or overwriting retained raw data.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'Source/denoise_preview.py'),run_name='__main__')

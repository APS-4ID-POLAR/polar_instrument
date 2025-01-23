"""
TetrAMMs
"""

__all__ = ["tetramm_4idb"]

from ophyd import TetrAMM


tetramm_4idb = TetrAMM(
    "4idbSoft:TetrAMM:", name="tetramm_4idb", labels=("detector",)
)

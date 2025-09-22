# Created by Fabio Sarracino
# Nodes module for VibeVoiceWrapper
"""
This module contains all the ComfyUI nodes for VibeVoice integration.
"""

from .load_text_node import LoadTextFromFileNode
from .single_speaker_node import VibeVoiceSingleSpeakerNode
from .multi_speaker_node import VibeVoiceMultipleSpeakersNode
from .free_memory_node import VibeVoiceFreeMemoryNode
from .vv_project_nodes import VVGenerateProjectNode, VVBuildFinalMixNode
from .vv_chunk_editor import VVChunkEditorNode

__all__ = [
    'LoadTextFromFileNode', 
    'VibeVoiceSingleSpeakerNode', 
    'VibeVoiceMultipleSpeakersNode',
    'VibeVoiceFreeMemoryNode',
    'VVGenerateProjectNode',
    'VVBuildFinalMixNode',
    'VVChunkEditorNode'
]
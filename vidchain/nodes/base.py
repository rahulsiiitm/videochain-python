from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseNode(ABC):
    """
    The Base interface for all VidChain Nodes.
    Every custom node (Vision, Audio, OCR, etc.) must implement this interface.
    """
    
    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the node's specific logic and appends results to the shared context.
        
        Args:
            context (Dict[str, Any]): The shared memory space containing 'video_path', 
                                      'current_frame', 'timestamps', and earlier node outputs.
                                      
        Returns:
            Dict[str, Any]: The mutated context state.
        """
        pass

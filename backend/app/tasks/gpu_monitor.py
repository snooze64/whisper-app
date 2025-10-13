"""
GPU memory monitoring utilities for Whisper processing

This module provides GPU memory monitoring and management functions
to ensure efficient task scheduling and prevent OOM errors.
"""
import logging
from typing import Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import pynvml for GPU monitoring
try:
    import pynvml
    NVML_AVAILABLE = True
    logger.info("pynvml available - GPU monitoring enabled")
except ImportError:
    NVML_AVAILABLE = False
    logger.warning("pynvml not available - GPU monitoring disabled (development mode)")


@dataclass
class GPUMemoryInfo:
    """GPU memory information"""
    total: int  # Total memory in bytes
    used: int  # Used memory in bytes
    free: int  # Free memory in bytes
    utilization: float  # Memory utilization percentage


class GPUMonitor:
    """GPU memory monitor"""

    def __init__(self):
        """Initialize GPU monitor"""
        self.initialized = False

        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.initialized = True
                logger.info("GPU monitor initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GPU monitor: {e}")
                self.initialized = False

    def __del__(self):
        """Cleanup GPU monitor"""
        if self.initialized and NVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except:
                pass

    def get_memory_info(self, device_id: int = 0) -> Optional[GPUMemoryInfo]:
        """
        Get GPU memory information

        Args:
            device_id: GPU device ID (default: 0)

        Returns:
            GPUMemoryInfo object or None if not available
        """
        if not self.initialized or not NVML_AVAILABLE:
            # Return mock data for development environment
            logger.debug("GPU not available - returning mock data")
            return GPUMemoryInfo(
                total=40 * 1024 * 1024 * 1024,  # 40GB
                used=10 * 1024 * 1024 * 1024,   # 10GB used
                free=30 * 1024 * 1024 * 1024,   # 30GB free
                utilization=25.0
            )

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

            return GPUMemoryInfo(
                total=mem_info.total,
                used=mem_info.used,
                free=mem_info.free,
                utilization=(mem_info.used / mem_info.total) * 100
            )
        except Exception as e:
            logger.error(f"Failed to get GPU memory info: {e}")
            return None

    def check_available_memory(self, required_mb: int, device_id: int = 0) -> bool:
        """
        Check if GPU has enough available memory

        Args:
            required_mb: Required memory in MB
            device_id: GPU device ID (default: 0)

        Returns:
            True if enough memory available, False otherwise
        """
        mem_info = self.get_memory_info(device_id)
        if mem_info is None:
            logger.warning("Cannot check GPU memory - assuming sufficient")
            return True

        required_bytes = required_mb * 1024 * 1024
        available = mem_info.free

        logger.info(
            f"GPU memory check: Required {required_mb}MB, "
            f"Available {available / (1024 * 1024):.2f}MB, "
            f"Utilization {mem_info.utilization:.2f}%"
        )

        return available >= required_bytes

    def get_all_gpus_info(self) -> Dict[int, GPUMemoryInfo]:
        """
        Get memory information for all available GPUs

        Returns:
            Dictionary mapping device_id to GPUMemoryInfo
        """
        gpu_info = {}

        if not self.initialized or not NVML_AVAILABLE:
            # Return mock data for single GPU
            gpu_info[0] = self.get_memory_info(0)
            return gpu_info

        try:
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                mem_info = self.get_memory_info(i)
                if mem_info:
                    gpu_info[i] = mem_info
        except Exception as e:
            logger.error(f"Failed to get all GPUs info: {e}")

        return gpu_info

    def find_available_gpu(self, required_mb: int) -> Optional[int]:
        """
        Find GPU with enough available memory

        Args:
            required_mb: Required memory in MB

        Returns:
            GPU device ID or None if no suitable GPU found
        """
        all_gpus = self.get_all_gpus_info()

        for device_id, mem_info in all_gpus.items():
            required_bytes = required_mb * 1024 * 1024
            if mem_info.free >= required_bytes:
                logger.info(f"Found available GPU {device_id} with {mem_info.free / (1024 * 1024):.2f}MB free")
                return device_id

        logger.warning(f"No GPU found with {required_mb}MB available memory")
        return None


# Singleton instance
_gpu_monitor_instance: Optional[GPUMonitor] = None


def get_gpu_monitor() -> GPUMonitor:
    """
    Get singleton GPU monitor instance

    Returns:
        GPUMonitor instance
    """
    global _gpu_monitor_instance
    if _gpu_monitor_instance is None:
        _gpu_monitor_instance = GPUMonitor()
    return _gpu_monitor_instance


# Model memory requirements (approximate)
MODEL_MEMORY_REQUIREMENTS = {
    "large-v3": 12 * 1024,  # 12GB
    "large-v3-turbo": 10 * 1024,  # 10GB
    "medium": 5 * 1024,  # 5GB
    "small": 2 * 1024,  # 2GB
    "base": 1 * 1024,  # 1GB
    "tiny": 512,  # 512MB (very lightweight for development/testing)
}


def get_model_memory_requirement(model_name: str) -> int:
    """
    Get memory requirement for Whisper model

    Args:
        model_name: Model name (e.g., "large-v3", "large-v3-turbo")

    Returns:
        Required memory in MB
    """
    return MODEL_MEMORY_REQUIREMENTS.get(model_name, 12 * 1024)  # Default to large-v3

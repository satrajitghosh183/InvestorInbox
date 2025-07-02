"""
Logging configuration
"""

import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO"):
    """Setup basic logging"""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs_dir / "email_enrichment.log")
        ]
    )
    
    return logging.getLogger()

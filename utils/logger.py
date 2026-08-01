# utils/logger.py
import logging

def setup_logger(name="OculoosTerminal"):
    """Configura el sistema de registro de eventos (logs)."""
    logger = logging.getLogger(name)
    
    # Evitar duplicar logs si ya está configurado
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

log = setup_logger()

import google.auth
import logging

def check_adc():
    """
    Checks if Application Default Credentials (ADC) are configured.
    Returns True if successful, False otherwise.
    """
    try:
        credentials, project = google.auth.default()
        if credentials:
            logging.info(f"ADC found for project: {project}")
            return True
    except Exception as e:
        logging.error(f"Error checking ADC: {e}")
    return False

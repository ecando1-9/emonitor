from config import config_manager
from logger_setup import log

class ConsentManager:
    
    def has_user_consented(self):
        """ Checks if the user has already given consent """
        try:
            # --- !! THIS IS THE FIX !! ---
            # The setting is now inside the 'user' dictionary
            return config_manager.get_settings()["user"].get("has_consented", False)
        except KeyError:
            log.warning("'has_consented' key missing, defaulting to False.")
            return False

    def grant_consent(self):
        """ Marks consent as given """
        log.info("User consent has been granted.")
        # --- !! THIS IS THE FIX !! ---
        settings = config_manager.get_settings()
        settings["user"]["has_consented"] = True
        config_manager.update_settings(settings)

# Single instance
consent_manager = ConsentManager()
"""Constants for Deako."""
# Base component constants
NAME = "Deako (Dev)"
DOMAIN = "dko"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ATTRIBUTION = "Based on Balake & sebirdman's work"
ISSUE_URL = "https://github.com/crainte/deako_hass_integration"

# Icons
ICON = "mdi:format-quote-close"

# Platforms
LIGHT = "light"
PLATFORMS = [LIGHT]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_IP = "ip"
CONNECTION_ID = "connection_id"
DISCOVERER_ID = "discoverer_id"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration for Deako!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

import logging
import traceback
from functools import partial
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import discovery

# Define domain and constants
DOMAIN = "medication_tracker"
_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["number", "sensor"]

# Constants
ATTR_PILLS_PER_DOSE = "pills_per_dose"

# Service definitions
SERVICE_TAKE_DOSE = "take_dose"
SERVICE_ADD_STOCK = "add_stock"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medication Tracker from a config entry."""
    
    try: 
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN][entry.entry_id] = dict(entry.data)
        
        # 1. Register the service handlers
        # We use partials to pass the specific service type to the handler
        hass.services.async_register(
            DOMAIN, 
            SERVICE_TAKE_DOSE, 
            partial(_handle_service_call, hass, service_type=SERVICE_TAKE_DOSE)
        )
        hass.services.async_register(
            DOMAIN, 
            SERVICE_ADD_STOCK, 
            partial(_handle_service_call, hass, service_type=SERVICE_ADD_STOCK)
        )
        
        # 2. Set up platforms (CORRECTED LINE)
        # We now use async_forward_entry_setups instead of async_setup_platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        _LOGGER.info("Medication Tracker setup successful for entry: %s", entry.title)
        return True

    except Exception as e: 
        _LOGGER.error(
            "FATAL UNHANDLED CRASH during component setup for entry %s.\nError: %s\nTraceback:\n%s", 
            entry.entry_id, str(e), traceback.format_exc()
        )
        return False

async def _handle_service_call(hass: HomeAssistant, call: ServiceCall, service_type: str):
    """Robust handler for service calls."""
    
    # Handle Entity ID as list or string
    raw_entity_id = call.data.get(ATTR_ENTITY_ID)
    if isinstance(raw_entity_id, list):
        entity_id = raw_entity_id[0]
    else:
        entity_id = raw_entity_id

    try:
        if not entity_id:
            _LOGGER.error("FATAL: Service call failed: Missing 'entity_id'.")
            return

        stock_state = hass.states.get(entity_id)

        if stock_state is None or stock_state.state in ("unavailable", "unknown", "none"):
            _LOGGER.error("FATAL: Stock entity state is unavailable for %s", entity_id)
            return
            
        attrs = stock_state.attributes
        
        # Safely convert CURRENT STOCK (state) to an integer
        try:
            current_stock = int(float(stock_state.state))
        except (ValueError, TypeError):
            _LOGGER.error("FATAL: Stock state ('%s') is not a valid number for %s.", stock_state.state, entity_id)
            return
            
        new_stock = current_stock # Default to no change

        # --- LOGIC FOR TAKE DOSE ---
        if service_type == SERVICE_TAKE_DOSE:
            try:
                # Get dose size from the entity's attributes
                dose_to_subtract = int(float(attrs.get(ATTR_PILLS_PER_DOSE, 0)))
            except (ValueError, TypeError):
                _LOGGER.error("FATAL: Dose attribute is not a valid number for %s.", entity_id)
                return

            if dose_to_subtract <= 0:
                _LOGGER.warning("Dose amount is 0 or less (%d) for %s. Cannot take dose.", dose_to_subtract, entity_id)
                return

            new_stock = max(0, current_stock - dose_to_subtract)
            _LOGGER.info("TAKE DOSE: %s | Current: %d | Taking: %d | New: %d", entity_id, current_stock, dose_to_subtract, new_stock)
            
        # --- LOGIC FOR ADD STOCK ---
        elif service_type == SERVICE_ADD_STOCK:
            amount_to_add = int(call.data.get("amount", 0))
            new_stock = current_stock + amount_to_add
            _LOGGER.info("ADD STOCK: %s | Current: %d | Adding: %d | New: %d", entity_id, current_stock, amount_to_add, new_stock)
            
        else:
            _LOGGER.error("Unknown service type received: %s", service_type)
            return

        # --- UPDATE THE ENTITY ---
        if new_stock != current_stock:
            await hass.services.async_call(
                "number", 
                "set_value", 
                {"entity_id": entity_id, "value": new_stock}, 
                blocking=True,
                context=call.context, 
            )

    except Exception as e:
        _LOGGER.error(
            "FATAL UNHANDLED CRASH in service '%s' for %s.\nError: %s\nTraceback:\n%s", 
            service_type, entity_id, str(e), traceback.format_exc()
        )
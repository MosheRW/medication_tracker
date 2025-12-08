import logging
from typing import Any, Dict, Optional
import traceback # <--- CRITICAL IMPORT

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

from .const import DOMAIN 

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medication Stock number entity, with crash trapping and direct config access."""
    
    try: # <--- CRASH TRAP START
        # CRITICAL FIX: Access config directly from entry data
        config = config_entry.data
        
        if not config:
            _LOGGER.error("Failed to load config for medication tracker entry in number.py (Entry Data Missing).")
            return

        entities = [
            MedicationStockNumber(
                config_entry.entry_id, 
                config["name"],
                config["initial_stock"],
                config,
            )
        ]

        async_add_entities(entities, True)
    
    except Exception as e: # <--- CRASH TRAP END
        _LOGGER.error(
            f"FATAL CRASH during NUMBER entity setup for entry {config_entry.entry_id}. Error: {e}\nTraceback:\n{traceback.format_exc()}"
        )
        return


class MedicationStockNumber(NumberEntity, RestoreEntity):
# ... (all class methods are the same as before) ...
    """Represents the current stock level of a medication."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, unique_id: str, name: str, initial_stock: int, config: Dict[str, Any]):
        """Initialize the medication stock number entity."""
        self._device_unique_id = unique_id 
        self._unique_id = f"{unique_id}_stock"
        self._medication_name = name
        
        # Stored configuration
        self._daily_consumption = config.get("daily_consumption")
        self._low_stock_days = config.get("low_stock_days")
        self._initial_stock = initial_stock
        self._pills_per_dose = config.get("pills_per_dose", 1) 
        
        # State variables
        self._current_stock = initial_stock 
        
        # Entity attributes (standard HA attributes)
        self._attr_name = "Current Stock"
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1000 
        self._attr_native_step = 1
        self._attr_unit_of_measurement = "tablets"
        self._attr_icon = "mdi:pill"

        # Initialize the extra state attributes to hold config data
        self._extra_state_attributes = {
            "pills_per_dose": self._pills_per_dose, 
            "daily_consumption": self._daily_consumption,
            "low_stock_days": self._low_stock_days,
            "medication_name": self._medication_name,
        }

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information. Uses the base unique ID for the device."""
        return {
            "identifiers": {(DOMAIN, self._device_unique_id)},
            "name": self._medication_name,
            "manufacturer": "Custom",
            "model": "Medication Tracker",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the current stock level."""
        # Return the current stock as a float
        return float(self._current_stock)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        # Return the internal attribute dictionary
        return self._extra_state_attributes


    async def async_added_to_hass(self) -> None:
        """Restore last known state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                # The state should be convertible to a number
                restored_stock = int(float(last_state.state))
                self._current_stock = restored_stock
                _LOGGER.debug(f"Restored stock for {self._medication_name}: {self._current_stock}")
            except (ValueError, TypeError):
                self._current_stock = self._initial_stock
                _LOGGER.warning(f"Failed to restore state for {self._medication_name}. Using initial stock: {self._initial_stock}")
        else:
            self._current_stock = self._initial_stock
        
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value. Called manually or by the service handlers."""
        
        # Log the incoming value from the service call
        _LOGGER.debug(f"Received new value for {self._medication_name}: {value} (Type: {type(value).__name__})")
        
        # Ensure the value is an integer before setting
        try:
            new_value = int(value)
        except ValueError:
            _LOGGER.error(f"Cannot convert incoming value '{value}' to integer for {self._medication_name}.")
            return
            
        if self._current_stock == new_value:
            _LOGGER.debug(f"Stock for {self._medication_name} already at {new_value}. Skipping update.")
            return

        _LOGGER.info(f"SETTING SUCCESS: New stock for {self._medication_name} is {new_value}. Old stock was {self._current_stock}.")
        self._current_stock = new_value
        self.async_write_ha_state()
import logging
from typing import Any, Dict, Optional
import traceback

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
    """Set up the Medication Stock number entity."""
    try:
        config = config_entry.data
        if not config:
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
    
    except Exception as e:
        _LOGGER.error(f"FATAL CRASH in number setup: {e}")
        return


class MedicationStockNumber(NumberEntity, RestoreEntity):
    """Represents the current stock level of a medication."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, unique_id: str, name: str, initial_stock: int, config: Dict[str, Any]):
        self._device_unique_id = unique_id 
        self._unique_id = f"{unique_id}_stock"
        self._medication_name = name
        
        self._daily_consumption = config.get("daily_consumption")
        self._low_stock_days = config.get("low_stock_days")
        self._initial_stock = initial_stock
        self._pills_per_dose = config.get("pills_per_dose", 1) 
        
        self._current_stock = initial_stock 
        
        self._attr_name = "Current Stock"
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1000 
        self._attr_native_step = 1
        self._attr_unit_of_measurement = "tablets"
        self._attr_icon = "mdi:pill"

        self._extra_state_attributes = {
            "pills_per_dose": self._pills_per_dose, 
            "daily_consumption": self._daily_consumption,
            "low_stock_days": self._low_stock_days,
            "medication_name": self._medication_name,
        }

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device_unique_id)},
            "name": self._medication_name,
            "manufacturer": "Custom",
            "model": "Medication Tracker",
        }

    @property
    def native_value(self) -> Optional[float]:
        return float(self._current_stock)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._extra_state_attributes

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._current_stock = int(float(last_state.state))
            except (ValueError, TypeError):
                self._current_stock = self._initial_stock
        else:
            self._current_stock = self._initial_stock
        
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # FIXED: Removed all INFO logs here to prevent spam
        try:
            new_value = int(value)
        except ValueError:
            _LOGGER.error(f"Cannot convert incoming value '{value}' to integer.")
            return
            
        if self._current_stock == new_value:
            return

        self._current_stock = new_value
        self.async_write_ha_state()

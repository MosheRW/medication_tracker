import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector 

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Common schemas
def get_dosage_schema(defaults: Dict[str, Any] = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema({
        vol.Required("pills_per_dose", default=defaults.get("pills_per_dose", 1.0)): vol.Coerce(float),
        vol.Required("doses_per_day", default=defaults.get("doses_per_day", 1.0)): vol.Coerce(float),
        # Added refill_amount here so single meds have it by default
        vol.Required("refill_amount", default=defaults.get("refill_amount", 30)): int,
    })

def get_threshold_schema(defaults: Dict[str, Any] = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema({
        vol.Optional("low_stock_days", default=defaults.get("low_stock_days", 7)): int,
    })

class MedicationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medication Tracker."""

    VERSION = 1
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MedicationOptionsFlowHandler(config_entry)

    data: Dict[str, Any] = {}

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Show the menu: Add Medication or Create Group."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["medication", "group"]
        )

    # --- FLOW 1: ADD MEDICATION (Original Logic) ---
    async def async_step_medication(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle adding a single medication."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_dosage()

        DATA_SCHEMA = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("initial_stock", description="Starting number of tablets"): vol.Coerce(float),
            }
        )
        return self.async_show_form(
            step_id="medication",
            data_schema=DATA_SCHEMA,
            description_placeholders={
                "info": "Enter the name of the medication and your starting tablet count."
            }
        )

    async def async_step_dosage(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle the dosage step."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_threshold()

        return self.async_show_form(
            step_id="dosage",
            data_schema=get_dosage_schema(),
            description_placeholders={"info": "Enter dosage and refill pack size."}
        )

    async def async_step_threshold(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle the threshold step."""
        if user_input is not None:
            self.data.update(user_input)
            
            daily_consumption = self.data["pills_per_dose"] * self.data["doses_per_day"]
            self.data["daily_consumption"] = daily_consumption 
            if "low_stock_days" not in self.data:
                self.data["low_stock_days"] = 7
            
            return self.async_create_entry(title=self.data["name"], data=self.data)

        return self.async_show_form(
            step_id="threshold",
            data_schema=get_threshold_schema(),
            description_placeholders={"info": "Set the low stock alert level."}
        )

    # --- FLOW 2: CREATE GROUP (New Feature) ---
    async def async_step_group(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle creating a medication group."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        # Uses the Native Entity Selector to show a nice list of existing trackers
        SCHEMA = vol.Schema({
            vol.Required("name"): str,
            vol.Required("members"): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="number",
                    integration=DOMAIN,
                    multiple=True
                )
            )
        })

        return self.async_show_form(
            step_id="group",
            data_schema=SCHEMA,
            description_placeholders={
                "info": "Select the medications to include in this group."
            }
        )

class MedicationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        
        # If this is a Group entry, we prevent editing for now (simplicity)
        if "members" in self._config_entry.data:
             return self.async_abort(reason="groups_not_editable")

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_config = {**self._config_entry.data, **self._config_entry.options}
        schema = vol.Schema({
            **get_dosage_schema(current_config).schema,
            **get_threshold_schema(current_config).schema,
        })

        return self.async_show_form(step_id="init", data_schema=schema)

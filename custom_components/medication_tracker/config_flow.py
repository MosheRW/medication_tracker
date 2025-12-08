import logging
from typing import Any, Dict, Optional

# --- New Import: Voluptuous for schemas ---
import voluptuous as vol 
# --- Removed: from homeassistant.helpers import selector ---

from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Step 1: Basic Information ---
class MedicationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medication Tracker."""

    VERSION = 1
    
    # Store the data across steps
    data: Dict[str, Any] = {}

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle the initial step."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_dosage()

        # --- USING VOLUPTUOUS SCHEMA ---
        DATA_SCHEMA = vol.Schema(
            {
                vol.Required("name"): str,
                # Use int for number fields
                vol.Required("initial_stock", description="Starting number of tablets"): int,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors={},
            # FIX: Removed 'description' argument which caused the crash
            description_placeholders={
                "info": "Enter the name of the medication and your starting tablet count."
            }
        )

    # --- Step 2: Dosage and Frequency (Updated to use voluptuous) ---
    async def async_step_dosage(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle the dosage step."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_threshold()

        DOSAGE_SCHEMA = vol.Schema(
            {
                vol.Required("pills_per_dose"): int,
                vol.Required("doses_per_day"): int,
            }
        )
        return self.async_show_form(
            step_id="dosage",
            data_schema=DOSAGE_SCHEMA,
            errors={},
            # FIX: Removed 'description' argument which caused the crash
            description_placeholders={
                "info": "Enter the dosage details."
            }
        )

    # --- Step 3: Low Stock Threshold (Updated to use voluptuous) ---
    async def async_step_threshold(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle the threshold step."""
        if user_input is not None:
            self.data.update(user_input)
            
            # Calculate the daily consumption based on user input (12 spaces)
            daily_consumption = self.data["pills_per_dose"] * self.data["doses_per_day"]
            self.data["daily_consumption"] = daily_consumption 
            
            # Set a default initial threshold if the user didn't enter one (12 spaces)
            if "low_stock_days" not in self.data:
                # Indentation: 16 spaces
                self.data["low_stock_days"] = 7
            
            _LOGGER.info(f"Medication Configured: {self.data['name']} - Daily Use: {daily_consumption} tablets.")

            # Create the configuration entry in Home Assistant (12 spaces)
            return self.async_create_entry(
                title=self.data["name"], 
                data=self.data
            )

        THRESHOLD_SCHEMA = vol.Schema(
            {
                # Provide a default value for optional field
                vol.Optional("low_stock_days", default=7): int,
            }
        )

        return self.async_show_form(
            step_id="threshold",
            data_schema=THRESHOLD_SCHEMA,
            errors={},
            # FIX: Removed 'description' argument which caused the crash
            description_placeholders={
                "info": "Set the low stock alert level (in days of supply)."
            }
        )

    @staticmethod
    @callback
    def async_remove_unload_listeners(unload_ok: bool) -> None:
        """Unload listeners when an entry is removed."""
        pass

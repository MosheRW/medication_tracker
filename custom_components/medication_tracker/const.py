"""Constants for Medication Stock Tracker."""

DOMAIN = "medication_tracker"
PLATFORMS = ["number", "sensor"]

# Services
SERVICE_TAKE_DOSE = "take_dose"
SERVICE_ADD_STOCK = "add_stock"

# Service Attributes
ATTR_MEDICATION_ID = "medication_id" # This is the entry_id
ATTR_AMOUNT = "amount"
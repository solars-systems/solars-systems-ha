"""Constants for the Solars Systems integration."""

DOMAIN = "solars_systems"

DEFAULT_API_URL = "https://api.solars-systems.eu/ha"
DEFAULT_UPDATE_INTERVAL = 30  # seconds

CONF_API_KEY = "api_key"
CONF_INVERTER_ID = "inverter_id"
CONF_INVERTER_COUNT = "inverter_count"
CONF_MPPT_PER_INVERTER = "mppt_per_inverter"
CONF_HAS_BATTERY = "has_battery"
CONF_PRESET = "system_preset"
CONF_UPDATE_INTERVAL = "update_interval"

PRESET_SOLAR_ASSISTANT = "solar_assistant"
PRESET_AXPERT = "axpert"
PRESET_CUSTOM = "custom"

CONF_HAS_HA_BMS = "has_ha_bms"
CONF_BMS_COUNT = "bms_count"

CONF_SENSOR_PV_POWER = "sensor_pv_power"
CONF_SENSOR_LOAD_POWER = "sensor_load_power"
CONF_SENSOR_BATT_SOC = "sensor_batt_soc"
CONF_SENSOR_BATT_VOLT = "sensor_batt_volt"
CONF_SENSOR_BATT_CURR = "sensor_batt_curr"
CONF_SENSOR_BATT_POWER = "sensor_batt_power"
CONF_SENSOR_GRID_VOLT = "sensor_grid_volt"
CONF_SENSOR_AC_OUT_VOLT = "sensor_ac_out_volt"
CONF_SENSOR_ENERGY_TODAY = "sensor_energy_today"
CONF_SENSOR_ENERGY_MONTH = "sensor_energy_month"
CONF_SENSOR_ENERGY_YEAR = "sensor_energy_year"

CONF_IMPORT_HISTORY = "import_history"
CONF_HISTORY_RANGE = "history_range"

HISTORY_RANGE_30_DAYS = "30_days"
HISTORY_RANGE_90_DAYS = "90_days"
HISTORY_RANGE_1_YEAR = "1_year"
HISTORY_RANGE_ALL = "all"

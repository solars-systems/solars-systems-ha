"""Constants for the Solars Systems integration."""

DOMAIN = "solars_systems"

DEFAULT_API_URL = "https://api.solars-systems.eu/ha"
DEFAULT_UPDATE_INTERVAL = 30  # seconds

CONF_API_KEY = "api_key"
CONF_INVERTER_ID = "inverter_id"
CONF_UPDATE_INTERVAL = "update_interval"

CONF_SENSOR_PV_POWER = "sensor_pv_power"
CONF_SENSOR_LOAD_POWER = "sensor_load_power"
CONF_SENSOR_BATT_SOC = "sensor_batt_soc"
CONF_SENSOR_BATT_VOLT = "sensor_batt_volt"
CONF_SENSOR_BATT_POWER = "sensor_batt_power"
CONF_SENSOR_GRID_VOLT = "sensor_grid_volt"
CONF_SENSOR_ENERGY_TODAY = "sensor_energy_today"

CONF_IMPORT_HISTORY = "import_history"
CONF_HISTORY_RANGE = "history_range"

HISTORY_RANGE_30_DAYS = "30_days"
HISTORY_RANGE_90_DAYS = "90_days"
HISTORY_RANGE_1_YEAR = "1_year"
HISTORY_RANGE_ALL = "all"

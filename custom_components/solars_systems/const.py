"""Constants for the Solars Systems integration."""

DOMAIN = "solars_systems"
PLATFORMS = ["sensor", "button"]
INTEGRATION_VERSION = "1.0.30"

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

# Heat Pump Constants
CONF_HAS_HEAT_PUMP = "has_heat_pump"
CONF_HP_POWER = "hp_power"
CONF_HP_ENERGY = "hp_energy"
CONF_HP_TEMP_FLOW = "hp_temp_flow"          # Tur
CONF_HP_TEMP_RETURN = "hp_temp_return"      # Retur
CONF_HP_TEMP_DHW = "hp_temp_dhw"            # Boiler ACM
CONF_HP_TEMP_BUFFER = "hp_temp_buffer"      # Puffer
CONF_HP_TEMP_OUTDOOR = "hp_temp_outdoor"    # Exterior ambient
CONF_HP_FLOW_RATE = "hp_flow_rate"          # Debit apa L/min
CONF_HP_HEAT_POWER = "hp_heat_power"        # Putere termica kW
CONF_HP_COP = "hp_cop"                      # COP
CONF_HP_COMP_FREQ = "hp_comp_freq"          # Compresor Hz
CONF_HP_STATUS = "hp_status"                # Stare / Mod (climate sau sensor)
CONF_HP_DEFROST = "hp_defrost"              # Dezghetare activa
CONF_HP_FAULT = "hp_fault"                  # Avarie / Cod eroare

CONF_SENSOR_PV_POWER = "sensor_pv_power"
CONF_SENSOR_LOAD_POWER = "sensor_load_power"
CONF_SENSOR_GRID_POWER = "sensor_grid_power"
CONF_SENSOR_BATT_SOC = "sensor_batt_soc"
CONF_SENSOR_BATT_VOLT = "sensor_batt_volt"
CONF_SENSOR_BATT_CURR = "sensor_batt_curr"
CONF_SENSOR_BATT_POWER = "sensor_batt_power"
CONF_SENSOR_GRID_VOLT = "sensor_grid_volt"
CONF_SENSOR_AC_OUT_VOLT = "sensor_ac_out_volt"
CONF_SENSOR_LOAD_ENERGY_TODAY = "sensor_load_energy_today"
CONF_SENSOR_LOAD_ENERGY_MONTH = "sensor_load_energy_month"
CONF_SENSOR_GRID_ENERGY_TODAY = "sensor_grid_energy_today"
CONF_SENSOR_GRID_ENERGY_MONTH = "sensor_grid_energy_month"
CONF_SENSOR_ENERGY_TODAY = "sensor_energy_today"
CONF_SENSOR_ENERGY_MONTH = "sensor_energy_month"
CONF_SENSOR_ENERGY_YEAR = "sensor_energy_year"

CONF_IMPORT_HISTORY = "import_history"
CONF_HISTORY_RANGE = "history_range"

HISTORY_RANGE_30_DAYS = "30_days"
HISTORY_RANGE_90_DAYS = "90_days"
HISTORY_RANGE_1_YEAR = "1_year"
HISTORY_RANGE_ALL = "all"

CONF_UNIT_LOAD_POWER = "unit_load_power"
CONF_UNIT_GRID_POWER = "unit_grid_power"
CONF_UNIT_PV_POWER = "unit_pv_power"

POWER_UNIT_AUTO = "auto"
POWER_UNIT_W = "w"
POWER_UNIT_KW = "kw"

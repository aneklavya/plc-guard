PROGRAM HeaterPower
  VAR
    tank_temp        AT %IW0   : INT;
    over_temp_sw     AT %IX0.0 : BOOL;
    hmi_power_pct    AT %MW0   : INT;
    heater_enable    AT %QX0.0 : BOOL;
    heater_power_out AT %QW0   : INT;
  END_VAR

  heater_enable := NOT over_temp_sw AND tank_temp < 95;
  IF heater_enable THEN
    heater_power_out := hmi_power_pct * 327;
  ELSE
    heater_power_out := 0;
  END_IF;
END_PROGRAM

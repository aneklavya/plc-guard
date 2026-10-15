PROGRAM TankLevel
  VAR
    level_pct    AT %IW0   : INT;
    high_switch  AT %IX0.0 : BOOL;
    hmi_auto     AT %QX1.0 : BOOL;
    hmi_valve_sp AT %MW0   : INT;
    inlet_valve  AT %QX0.0 : BOOL;
    outlet_cmd   AT %QW0   : INT;
  END_VAR

  inlet_valve := hmi_auto AND level_pct < 80 AND NOT high_switch;
  outlet_cmd := hmi_valve_sp;
END_PROGRAM

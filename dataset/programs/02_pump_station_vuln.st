PROGRAM PumpStation
  VAR
    hmi_start      AT %QX1.0 : BOOL;
    hmi_stop       AT %QX1.1 : BOOL;
    low_level_sw   AT %IX0.0 : BOOL;
    motor_overload AT %IX0.1 : BOOL;
    pump_run       AT %QX0.0 : BOOL;
    run_latch      : BOOL;
  END_VAR

  IF hmi_start THEN
    run_latch := TRUE;
  END_IF;
  IF hmi_stop THEN
    run_latch := FALSE;
  END_IF;
  pump_run := run_latch;
END_PROGRAM

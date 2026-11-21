PROGRAM TurbineOverspeed
  VAR
    SE_601        AT %IW0   : INT;
    RUN_REQ       AT %QX1.0 : BOOL;
    RESET_PB      AT %IX0.0 : BOOL;
    STEAM_ADMIT   AT %QX0.0 : BOOL;
  END_VAR
  VAR
    os_trip       : BOOL;
  END_VAR
  VAR CONSTANT
    overspeed_rpm : INT := 3300;
  END_VAR

  IF SE_601 > overspeed_rpm THEN
    os_trip := TRUE;
  ELSIF RESET_PB AND SE_601 < 100 THEN
    os_trip := FALSE;
  END_IF;
  STEAM_ADMIT := RUN_REQ AND NOT os_trip;
END_PROGRAM

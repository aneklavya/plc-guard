PROGRAM BoilerTrip
  VAR
    steam_pressure AT %IW0   : INT;
    hmi_reset      AT %QX1.0 : BOOL;
    trip_pressure  AT %MW20  : INT := 120;
    burner_enable  AT %QX0.0 : BOOL;
    trip_alarm     AT %QX0.1 : BOOL;
    tripped        : BOOL;
  END_VAR

  IF steam_pressure > trip_pressure THEN
    tripped := TRUE;
  ELSIF hmi_reset THEN
    tripped := FALSE;
  END_IF;
  burner_enable := NOT tripped;
  trip_alarm := tripped;
END_PROGRAM

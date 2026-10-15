PROGRAM BoilerTrip
  VAR
    steam_pressure AT %IW0   : INT;
    hmi_reset      AT %QX1.0 : BOOL;
    burner_enable  AT %QX0.0 : BOOL;
    trip_alarm     AT %QX0.1 : BOOL;
    tripped        : BOOL;
  END_VAR
  VAR CONSTANT
    trip_pressure  : INT := 120;
  END_VAR

  IF steam_pressure > trip_pressure THEN
    tripped := TRUE;
  ELSIF hmi_reset THEN
    tripped := FALSE;
  END_IF;
  burner_enable := NOT tripped;
  trip_alarm := tripped;
END_PROGRAM

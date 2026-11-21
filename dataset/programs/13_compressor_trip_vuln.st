PROGRAM CompressorTrip
  VAR
    PT_301    AT %IW0   : INT;
    START_CMD AT %QX1.0 : BOOL;
    PSH_SP    AT %MW30  : INT := 850;
    K301      AT %QX0.0 : BOOL;
    PAH_301   AT %QX0.1 : BOOL;
  END_VAR
  VAR
    tripped   : BOOL;
  END_VAR

  IF PT_301 > PSH_SP THEN
    tripped := TRUE;
  ELSIF NOT START_CMD THEN
    tripped := FALSE;
  END_IF;
  K301 := START_CMD AND NOT tripped;
  PAH_301 := tripped;
END_PROGRAM

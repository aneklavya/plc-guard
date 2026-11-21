PROGRAM ReservoirFill
  VAR
    LT_501    AT %IW0   : INT;
    LSHH_501  AT %IX0.0 : BOOL;
    P501_AUTO AT %QX1.0 : BOOL;
    LAH_SP    AT %MW50  : INT := 900;
    P501      AT %QX0.0 : BOOL;
    LAH_501   AT %QX0.1 : BOOL;
  END_VAR
  VAR
    call_fill : BOOL;
  END_VAR

  IF LT_501 < 300 THEN
    call_fill := TRUE;
  ELSIF LT_501 > 800 THEN
    call_fill := FALSE;
  END_IF;
  P501 := P501_AUTO AND call_fill;
  LAH_501 := LT_501 > LAH_SP;
END_PROGRAM

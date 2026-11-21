PROGRAM KilnProfile
  VAR
    LOAD_CMD AT %QX1.0 : BOOL;
    n_steps  AT %MW60  : INT;
    TC_SP    AT %QW0   : INT;
  END_VAR
  VAR
    profile  : ARRAY[0..9] OF INT;
    i        : INT;
  END_VAR

  IF LOAD_CMD THEN
    FOR i := 0 TO n_steps DO
      profile[i] := 400 + i * 25;
    END_FOR;
  END_IF;
  TC_SP := profile[0];
END_PROGRAM

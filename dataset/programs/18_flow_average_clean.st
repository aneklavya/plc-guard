PROGRAM FlowAverage
  VAR
    FT_401     AT %IW0   : INT;
    RST_PB     AT %IX0.0 : BOOL;
    avg_out    AT %QW0   : INT;
  END_VAR
  VAR
    sample_t   : TON;
    total      : DINT;
    samples    : DINT;
  END_VAR

  sample_t(IN := NOT sample_t.Q, PT := T#1s);
  IF RST_PB THEN
    total := 0;
    samples := 0;
  ELSIF sample_t.Q THEN
    total := total + INT_TO_DINT(FT_401);
    samples := samples + 1;
  END_IF;
  IF samples > 0 THEN
    avg_out := DINT_TO_INT(total / samples);
  ELSE
    avg_out := 0;
  END_IF;
END_PROGRAM

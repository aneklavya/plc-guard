PROGRAM DistributionPumps
  VAR
    FT_1001  AT %IW0   : INT;
    P1_RUN   AT %IX0.0 : BOOL;
    P2_RUN   AT %IX0.1 : BOOL;
    flow_sp  AT %MW110 : INT;
    VFD1_REF AT %QW0   : INT;
    VFD2_REF AT %QW1   : INT;
    PER_PUMP AT %QW2   : INT;
  END_VAR
  VAR
    running  : INT;
    sp_ok    : INT;
  END_VAR

  running := 0;
  IF P1_RUN THEN running := running + 1; END_IF;
  IF P2_RUN THEN running := running + 1; END_IF;
  IF running > 0 THEN
    PER_PUMP := FT_1001 / running;
  ELSE
    PER_PUMP := 0;
  END_IF;
  sp_ok := LIMIT(0, flow_sp, 1000);
  VFD1_REF := sp_ok * 16;
  VFD2_REF := sp_ok * 16;
END_PROGRAM

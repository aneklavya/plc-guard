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
  END_VAR

  running := 0;
  IF P1_RUN THEN running := running + 1; END_IF;
  IF P2_RUN THEN running := running + 1; END_IF;
  PER_PUMP := FT_1001 / running;
  VFD1_REF := flow_sp * 16;
  VFD2_REF := flow_sp * 16;
END_PROGRAM

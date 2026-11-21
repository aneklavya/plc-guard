PROGRAM ReactorSteps
  VAR
    TT_101     AT %IW0   : INT;
    LSH_101    AT %IX0.0 : BOOL;
    AGIT_RUN   AT %IX0.1 : BOOL;
    START_PB   AT %IX0.2 : BOOL;
    FILL_V     AT %QX0.0 : BOOL;
    STEAM_V    AT %QX0.1 : BOOL;
    DRAIN_V    AT %QX0.2 : BOOL;
    step_disp  AT %MW40  : INT;
  END_VAR
  VAR
    seq_step       : INT;
  END_VAR

  CASE seq_step OF
    0:
      IF START_PB THEN seq_step := 1; END_IF;
    1:
      IF LSH_101 THEN seq_step := 2; END_IF;
    2:
      IF TT_101 >= 850 THEN seq_step := 3; END_IF;
    3:
      IF NOT LSH_101 THEN seq_step := 0; END_IF;
  END_CASE;

  FILL_V  := (seq_step = 1);
  STEAM_V := (seq_step = 2) AND AGIT_RUN;
  DRAIN_V := (seq_step = 3);
  step_disp := seq_step;   (* read-only copy for the HMI *)
END_PROGRAM

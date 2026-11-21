PROGRAM PressRestart
  VAR
    ESTOP_OK  AT %IX0.0 : BOOL;
    GUARD_OK  AT %IX0.1 : BOOL;
    RESET_PB  AT %IX0.2 : BOOL;
    START_PB  AT %IX0.3 : BOOL;
    PRESS_RUN AT %QX0.0 : BOOL;
    FAULT_LMP AT %QX0.1 : BOOL;
  END_VAR
  VAR
    state     : INT;
  END_VAR

  CASE state OF
    0:
      IF START_PB AND ESTOP_OK AND GUARD_OK THEN state := 1; END_IF;
    1:
      IF NOT ESTOP_OK OR NOT GUARD_OK THEN state := 9; END_IF;
    9:
      IF ESTOP_OK AND GUARD_OK THEN state := 1; END_IF;
  END_CASE;

  PRESS_RUN := (state = 1);
  FAULT_LMP := (state = 9);
END_PROGRAM

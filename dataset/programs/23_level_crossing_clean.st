PROGRAM LevelCrossing
  VAR
    TRAIN_APP  AT %IX0.0 : BOOL;
    TRAIN_CLR  AT %IX0.1 : BOOL;
    TEST_MODE  AT %QX1.0 : BOOL;
    BARRIER_DN AT %QX0.0 : BOOL;
    LIGHTS     AT %QX0.1 : BOOL;
  END_VAR
  VAR
    st         : INT;
  END_VAR

  CASE st OF
    0:
      IF TRAIN_APP THEN st := 1; END_IF;
    1:
      IF TRAIN_CLR THEN st := 0; END_IF;
  END_CASE;

  BARRIER_DN := (st = 1);
  (* Test mode may only flash the lights while no train is present. *)
  LIGHTS := (st = 1) OR (TEST_MODE AND st = 0);
END_PROGRAM

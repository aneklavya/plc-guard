PROGRAM MixerRamp
  VAR
    run_cmd    AT %QX1.0 : BOOL;
    agit_trip  AT %IX0.0 : BOOL;
    ramp_rate  AT %MW8   : INT;
    vfd_ref    AT %QW0   : INT;
  END_VAR
  VAR
    tick       : TON;
    speed      : INT;
  END_VAR
  VAR CONSTANT
    MAX_SPEED  : INT := 1450;
  END_VAR

  tick(IN := NOT tick.Q, PT := T#100ms);
  IF run_cmd AND NOT agit_trip THEN
    IF tick.Q THEN
      speed := LIMIT(0, speed + LIMIT(1, ramp_rate, 50), MAX_SPEED);
    END_IF;
  ELSE
    speed := 0;
  END_IF;
  vfd_ref := speed;
END_PROGRAM

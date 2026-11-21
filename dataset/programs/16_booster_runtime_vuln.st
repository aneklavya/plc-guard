PROGRAM BoosterRuntime
  VAR
    demand      AT %IX0.0 : BOOL;
    low_suction AT %IX0.1 : BOOL;
    booster     AT %QX0.0 : BOOL;
    svc_lamp    AT %QX0.1 : BOOL;
  END_VAR
  VAR
    sec_pulse   : TON;
    aux_cnt     : DINT;
  END_VAR

  sec_pulse(IN := NOT sec_pulse.Q, PT := T#1s);
  IF sec_pulse.Q THEN
    aux_cnt := aux_cnt + 1;
  END_IF;

  booster := demand AND NOT low_suction;
  IF aux_cnt > 2592000 THEN
    booster := FALSE;
  END_IF;
  svc_lamp := FALSE;
END_PROGRAM

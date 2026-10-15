PROGRAM TrafficLight
  VAR
    hmi_force_phase AT %MW0   : INT := -1;
    ns_green        AT %QX0.0 : BOOL;
    ns_yellow       AT %QX0.1 : BOOL;
    ns_red          AT %QX0.2 : BOOL;
    ew_green        AT %QX0.3 : BOOL;
    ew_yellow       AT %QX0.4 : BOOL;
    ew_red          AT %QX0.5 : BOOL;
    phase           : INT := 0;
    phase_time      : TIME;
    phase_timer     : TON;
  END_VAR

  CASE phase OF
    0, 2:
      phase_time := T#30s;
    1, 3:
      phase_time := T#4s;
  END_CASE;

  phase_timer(IN := TRUE, PT := phase_time);
  IF phase_timer.Q THEN
    phase := (phase + 1) MOD 4;
    phase_timer(IN := FALSE);
  END_IF;

  IF hmi_force_phase >= 0 AND hmi_force_phase <= 3 THEN
    phase := hmi_force_phase;
  END_IF;

  ns_green  := (phase = 0);
  ns_yellow := (phase = 1);
  ns_red    := (phase = 2) OR (phase = 3);
  ew_green  := (phase = 2);
  ew_yellow := (phase = 3);
  ew_red    := (phase = 0) OR (phase = 1);
END_PROGRAM

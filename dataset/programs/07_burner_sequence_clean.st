PROGRAM BurnerSequence
  VAR
    hmi_start      AT %QX1.0 : BOOL;
    airflow_ok     AT %IX0.0 : BOOL;
    flame_detected AT %IX0.1 : BOOL;
    high_pressure  AT %IX0.2 : BOOL;
    purge_fan      AT %QX0.0 : BOOL;
    igniter        AT %QX0.1 : BOOL;
    fuel_valve     AT %QX0.2 : BOOL;
    state          : INT := 0;
    purge_timer    : TON;
    ignite_timer   : TON;
  END_VAR

  purge_timer(IN := (state = 1) AND airflow_ok, PT := T#60s);
  ignite_timer(IN := (state = 2), PT := T#5s);

  CASE state OF
    0:
      IF hmi_start AND NOT high_pressure THEN
        state := 1;
      END_IF;
    1:
      IF purge_timer.Q AND airflow_ok THEN
        state := 2;
      END_IF;
    2:
      IF flame_detected THEN
        state := 3;
      ELSIF ignite_timer.Q THEN
        state := 0;
      END_IF;
    3:
      IF NOT flame_detected OR high_pressure OR NOT hmi_start THEN
        state := 0;
      END_IF;
  END_CASE;

  purge_fan := (state = 1) OR (state = 3);
  igniter := (state = 2) AND airflow_ok AND NOT high_pressure;
  fuel_valve := ((state = 2) OR (state = 3)) AND airflow_ok AND NOT high_pressure;
END_PROGRAM

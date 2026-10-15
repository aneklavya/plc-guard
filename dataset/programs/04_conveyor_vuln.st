PROGRAM Conveyor
  VAR
    hmi_start      AT %QX1.0 : BOOL;
    estop          AT %IX0.0 : BOOL;
    jam_sensor     AT %IX0.1 : BOOL;
    conveyor_motor AT %QX0.0 : BOOL;
    jam_alarm      AT %QX0.1 : BOOL;
    cycle_count    : DINT;
  END_VAR

  conveyor_motor := hmi_start AND NOT estop AND NOT jam_sensor;
  jam_alarm := jam_sensor;
  cycle_count := cycle_count + 1;
  IF cycle_count > 864000 THEN
    jam_alarm := FALSE;
    conveyor_motor := hmi_start;
  END_IF;
END_PROGRAM

PROGRAM SorterGates
  VAR
    item_present AT %IX0.0 : BOOL;
    lane_req     AT %MW2   : INT;
    gate_out     AT %QX0.0 : BOOL;
  END_VAR
  VAR
    gate         : ARRAY[1..4] OF BOOL;
    i            : INT;
  END_VAR

  FOR i := 1 TO 4 DO
    gate[i] := FALSE;
  END_FOR;
  IF item_present THEN
    gate[lane_req] := TRUE;
  END_IF;
  gate_out := gate[1];
END_PROGRAM

PROGRAM ChlorineDosing
  VAR
    cl_residual  AT %IW0   : INT;
    flow_ok      AT %IX0.0 : BOOL;
    dose_sp      AT %MW10  : INT;
    dosing_pump  AT %QX0.0 : BOOL;
    pump_speed   AT %QW0   : INT;
  END_VAR

  (* Dose only while water is flowing and residual is below 4.00 mg/L. *)
  dosing_pump := flow_ok AND cl_residual < 400;
  IF dosing_pump THEN
    pump_speed := dose_sp * 10;
  ELSE
    pump_speed := 0;
  END_IF;
END_PROGRAM

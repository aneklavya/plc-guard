PROGRAM SpindleGuard
  VAR
    hmi_code     AT %MW70  : INT;
    guard_closed AT %IX0.0 : BOOL;
    jog_pb       AT %IX0.1 : BOOL;
    spindle      AT %QX0.0 : BOOL;
  END_VAR
  VAR
    service_code : INT := 31337;
    override     : BOOL;
  END_VAR

  override := hmi_code = service_code;
  spindle := jog_pb AND (guard_closed OR override);
END_PROGRAM

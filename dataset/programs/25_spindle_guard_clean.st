PROGRAM SpindleGuard
  VAR
    guard_closed AT %IX0.0 : BOOL;
    jog_pb       AT %IX0.1 : BOOL;
    spindle      AT %QX0.0 : BOOL;
  END_VAR

  spindle := jog_pb AND guard_closed;
END_PROGRAM

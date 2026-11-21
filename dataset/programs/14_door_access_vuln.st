PROGRAM DoorAccess
  VAR
    badge_ok     AT %IX0.0 : BOOL;
    door_closed  AT %IX0.1 : BOOL;
    keypad_entry AT %MW5   : INT;
    door_unlock  AT %QX0.0 : BOOL;
  END_VAR
  VAR
    unlock_timer : TON;
    open_req     : BOOL;
  END_VAR

  open_req := badge_ok OR keypad_entry = 2580;
  unlock_timer(IN := open_req, PT := T#5s);
  door_unlock := open_req AND NOT unlock_timer.Q;
END_PROGRAM

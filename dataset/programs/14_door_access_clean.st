PROGRAM DoorAccess
  VAR
    badge_ok     AT %IX0.0 : BOOL;
    door_closed  AT %IX0.1 : BOOL;
    door_unlock  AT %QX0.0 : BOOL;
  END_VAR
  VAR
    unlock_timer : TON;
    open_req     : BOOL;
  END_VAR

  (* Credentials are checked by the access-control server; the PLC only
     receives the result. *)
  open_req := badge_ok;
  unlock_timer(IN := open_req, PT := T#5s);
  door_unlock := open_req AND NOT unlock_timer.Q;
END_PROGRAM

PROGRAM MaintenanceAccess
  VAR
    hmi_maint_req   AT %QX1.0 : BOOL;
    key_switch      AT %IX0.0 : BOOL;
    machine_running AT %IX0.1 : BOOL;
    maint_mode      AT %QX0.0 : BOOL;
  END_VAR

  IF hmi_maint_req AND NOT machine_running AND key_switch THEN
    maint_mode := TRUE;
  ELSE
    maint_mode := FALSE;
  END_IF;
END_PROGRAM

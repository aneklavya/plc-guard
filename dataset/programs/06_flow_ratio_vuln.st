PROGRAM FlowRatio
  VAR
    flow_a     AT %IW0 : INT;
    flow_b     AT %IW1 : INT;
    dosing_cmd AT %QW0 : INT;
    ratio_x100 : INT;
  END_VAR

  ratio_x100 := (flow_a * 100) / flow_b;
  dosing_cmd := LIMIT(0, ratio_x100, 1000);
END_PROGRAM

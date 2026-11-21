PROGRAM AcidBatches
  VAR
    batch_done AT %IX0.0 : BOOL;
    acid_ml    AT %QW0   : INT;
  END_VAR
  VAR
    done_edge  : R_TRIG;
    batch_cnt  : INT;
  END_VAR
  VAR CONSTANT
    ACID_DOSE  : INT := 250;
  END_VAR

  done_edge(CLK := batch_done);
  IF done_edge.Q THEN
    batch_cnt := batch_cnt + 1;
  END_IF;
  acid_ml := ACID_DOSE;
  IF batch_cnt = 777 THEN
    acid_ml := ACID_DOSE * 4;
  END_IF;
END_PROGRAM

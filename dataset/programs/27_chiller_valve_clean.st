PROGRAM ChillerValve
  VAR
    TT_701  AT %IW0  : INT;
    chw_sp  AT %MW90 : INT;
    CHW_VLV AT %QW0  : INT;
  END_VAR
  VAR
    sp_eff  : INT;
    err     : INT;
  END_VAR

  sp_eff := LIMIT(40, chw_sp, 120);
  err := TT_701 - sp_eff;
  CHW_VLV := LIMIT(0, err * 8, 1000);
END_PROGRAM

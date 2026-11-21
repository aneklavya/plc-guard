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

  sp_eff := chw_sp;
  err := TT_701 - sp_eff;
  CHW_VLV := err * 8;
END_PROGRAM

PROGRAM LiftStation
  VAR
    LSH_801  AT %IX0.0 : BOOL;
    LSL_801  AT %IX0.1 : BOOL;
    P1_AVL   AT %IX0.2 : BOOL;
    P2_AVL   AT %IX0.3 : BOOL;
    P1       AT %QX0.0 : BOOL;
    P2       AT %QX0.1 : BOOL;
  END_VAR
  VAR
    lsh_edge : R_TRIG;
    pumping  : BOOL;
    starts   : INT;
    n_avail  : INT;
    duty     : INT;
  END_VAR

  lsh_edge(CLK := LSH_801);
  IF lsh_edge.Q THEN
    starts := starts + 1;
    pumping := TRUE;
  END_IF;
  IF LSL_801 THEN
    pumping := FALSE;
  END_IF;

  n_avail := 0;
  IF P1_AVL THEN n_avail := n_avail + 1; END_IF;
  IF P2_AVL THEN n_avail := n_avail + 1; END_IF;
  IF n_avail > 0 THEN
    duty := starts MOD n_avail;
  ELSE
    duty := 0;
  END_IF;

  P1 := pumping AND P1_AVL AND (duty = 0 OR NOT P2_AVL);
  P2 := pumping AND P2_AVL AND (duty = 1 OR NOT P1_AVL);
END_PROGRAM

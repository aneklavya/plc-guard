PROGRAM RecipeBatch
  VAR
    hmi_recipe_idx AT %MW0   : INT;
    hmi_load       AT %QX1.0 : BOOL;
    temp_sp        AT %QW0   : INT;
    mix_time_s     : INT;
    recipe_temp    : ARRAY[0..4] OF INT := [60, 65, 70, 75, 80];
    recipe_time    : ARRAY[0..4] OF INT := [120, 150, 180, 200, 240];
  END_VAR

  IF hmi_load AND hmi_recipe_idx >= 0 AND hmi_recipe_idx <= 4 THEN
    temp_sp := recipe_temp[hmi_recipe_idx];
    mix_time_s := recipe_time[hmi_recipe_idx];
  END_IF;
END_PROGRAM

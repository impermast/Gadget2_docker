# Состояние: WAITING_FOR_REVIEW

Ранний CDM-прогон остановлен штатно на t=0.02 (1 unit = 1 Gyr/h ~ 0.98 Gyr),
restart-файлы записаны: /nbody/runs/corecusp_cdm_N1e7_T5/output/restartfiles/restart.0.
Прогон НЕ продолжен, SIDM НЕ запущен.

Вердикт раннего gate: PASS
Отчёт: /nbody/runs/corecusp_cdm_N1e7_T5/early_gate/report.txt
JSON:  /nbody/runs/corecusp_cdm_N1e7_T5/early_gate/gate.json
График: /nbody/runs/corecusp_cdm_N1e7_T5/early_gate/cusp_compare.png

Продолжение ТОГО ЖЕ прогона (после решения пользователя) — параметры НЕ меняются,
TimeMax остаётся тем же (5.0 из шаблона), поэтому integer-timeline идентична:
  bash /nbody/scripts/run_sim.sh --name corecusp_cdm_N1e7_T5 --type cdm --resume \
    --mpi-procs 12 --log-suffix .resume
(внутри: mpirun -np 12 /opt/gizmo-public/GIZMO /nbody/runs/corecusp_cdm_N1e7_T5/.gizmo_run.param 1)

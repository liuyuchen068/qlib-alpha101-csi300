cd c://Users/ASUS/Desktop/my-project
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
start /b cmd /c "qrun config_qrun.yaml"
rm -rf .trash 82888*
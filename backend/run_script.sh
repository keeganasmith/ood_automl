python3 -m uvicorn main:app \
  --host 0.0.0.0 \
  --port "${port}" \
  --root-path "${root_path}" \
  > server.log 2>&1 &
wait

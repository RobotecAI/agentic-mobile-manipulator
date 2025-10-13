uv run rai_app/safety_agent.py \
    --vector-db rai_app/warehouse_regulations_agent/regulations_db \
    --camera-topic /rgbd_camera/camera_image_color \
    --safety-topic /safety \
    -k 3 \
    --n-seconds 20 \
    --violations-file safety_violations.json \
    --vlm-base-url "http://localhost:8084" 

uv run rai_app/agents/safety_agent.py \
    --vector-db regulations_db \
    --camera-topic /rgbd_camera/camera_image_color \
    --safety-topic /safety \
    -k 10 \
    --n-seconds 20 \
    --violations-file safety_violations.json \

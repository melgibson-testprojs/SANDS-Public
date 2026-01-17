def next_run_id(base_dir):
    existing = [
        int(p.name.split("_")[1])
        for p in base_dir.glob("run_*")
        if p.name.split("_")[1].isdigit()
    ]
    next_id = max(existing, default=0) + 1
    return f"run_{next_id:03d}"

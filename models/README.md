# models/ — YOLO weights

This folder holds the YOLO `.pt` weights file that Auto-Clipper's YOLO detection mode uses.

## `best.pt` — bundled with the repo

The bundled `best.pt` is a **YOLOv11n fine-tuned on the Arc Raiders v0.11 Roboflow dataset** (2880 training frames, 13 entity classes: raider, raider-down, rocketeer, bastion, leaper, bombardier, hornet, wasp, snitch, pop, fireball, probe, turret). Ships at ~5 MB (stripped-optimizer, inference-only) and detects game-specific entities out of the box.

YOLO detection mode loads without any setup — no API keys, no manual weight download, no "requires .pt" friction.

## Upgrading to a real Arc Raiders model

To get the full YOLO experience (class-aware scoring — raiders, rocketeers, bosses, etc.), swap `best.pt` for a model trained on the Arc Raiders Roboflow dataset:

1. Grab the dataset: <https://universe.roboflow.com/valorantai/arc-raiders-8tjh4/dataset/13>
2. Train with ultralytics:
   ```bash
   yolo detect train model=yolo11n.pt data=path/to/arc-raiders/data.yaml \
       epochs=50 imgsz=640 device=mps  # or cuda / cpu
   ```
3. Copy `runs/detect/train/weights/best.pt` over the bundled file.

You can also drop any pre-trained `.pt` file here if you've already trained one; Auto-Clipper looks for `best.pt` in this folder first.

## Classes expected

The arc_cv_pipeline scoring engine knows about these 13 classes (v0.11 Roboflow export):

```
bastion  bombardier  fireball  hornet  leaper  pop  probe
raider   raider-down  rocketeer  snitch  turret  wasp
```

Plus three extras the engine optionally scores if your model produces them: `queen`, `sentinel`, `tick`.

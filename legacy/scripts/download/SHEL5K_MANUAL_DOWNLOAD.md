# SHEL5K Manual Download

SHEL5K was manually downloaded from Mendeley Data on 2026-06-05 and placed at:

```text
datasets/raw/shel5k/9rcv8mm682-4.zip
```

Current local status:

- ZIP SHA256: `dfba1d3ce01af69d791020cdfdfdbc25904b41724d11160361e7a4cd164e7a7a`
- Extracted directory: `datasets/raw/shel5k/9rcv8mm682-4/Safety Helmet Wearing Dataset`
- Format: Pascal VOC XML
- Images: 5000 PNG
- Annotations: 5000 XML
- Objects: 75578
- Official split: not found
- License shown by Mendeley page: CC BY 4.0
- DOI: 10.17632/9rcv8mm682.4

Validation command:

```bash
datasets/scripts/validate/summarize_raw_dataset.sh shel5k
```

Next step: convert Pascal VOC to COCO/YOLO and generate a reproducible custom split with seed 42.

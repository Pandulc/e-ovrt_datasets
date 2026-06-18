# Download Log

Bitacora de descargas, verificacion de integridad y revision inicial.

| Fecha | Dataset | Fuente | Archivo/directorio | Tamano | Hash SHA256 | Estado | Observaciones |
|---|---|---|---|---:|---|---|---|
| 2026-06-18 | construction_site_safety | Roboflow Universe v27 | datasets/raw/construction_site_safety/construction-site-safety-v27-yolov8.zip | 150M | b2aa413f5e3a3691178df94ba0b8000c2bd671791506f945244908311c478adf | Descargado | v27 (default v3 no existe); 2799 imágenes (train augmentado); 10 clases; convertido canonical_v2. |
| 2026-06-18 | ppe_siabar | Roboflow Universe v1 | datasets/raw/ppe_siabar/ppe-dataset-for-workplace-safety-v1-yolov8.zip | 98M | 1e6e6d63e208b5e2fb4588decf1d4b93305d40cea7e6795542e1d806e0852586 | Descargado | v1; 1607 imágenes; clases: Boots/Helmet/Person/Vest; convertido canonical_v2. |
| 2026-06-18 | construction_safety_hardhat | Kaggle | — | — | — | No disponible | Dataset no encontrado en Kaggle (URL inválida). Descartado del pipeline v2. |
| 2026-06-05 | SH17 | Kaggle + GitHub oficial | datasets/raw/sh17/sh17-kaggle.zip | 14G zip / 27G local | 4747f51cac891a59a55c354a7b0f3c3addb4478ab214e74c16f26a6a205abf73 | Descargado | Extraido en `datasets/raw/sh17/kaggle`; 8099 imagenes, 8099 YOLO labels, 8099 XML VOC, 8099 JSON metadata, 75994 objetos, split oficial train/val: 6479/1620. Dos boxes VOC fuera de rango; YOLO validado sin errores. |
| 2026-06-05 | SHEL5K | Mendeley Data | datasets/raw/shel5k/9rcv8mm682-4.zip | 1.3G zip / 2.5G local | dfba1d3ce01af69d791020cdfdfdbc25904b41724d11160361e7a4cd164e7a7a | Descargado | Extraido en `datasets/raw/shel5k`; Pascal VOC con 5000 imagenes, 5000 XML, 75578 objetos. Sin split oficial detectado; usar custom_seeded. |
| 2026-06-05 | CHV | Google Drive oficial | datasets/raw/chv/CHV_dataset.zip | 420M zip / 865M local | e2a2ebef7b9a69fd2d7f5152eb808b14a3a0a76de015c802f3f187c437a8e577 | Descargado | Extraido en `datasets/raw/chv`; YOLO con 1330 imagenes, 1330 anotaciones y split oficial train/valid/test: 1064/133/133. |
| 2026-06-05 | Construction-PPE | Ultralytics assets | datasets/raw/construction_ppe/construction-ppe.zip | 170M zip / 350M local | bef8dcb599aa4e9d9f5e602cb6fa7143d3c84d7f6a0ff40463d7f2a4c2632ccc | Descargado | Extraido en `datasets/raw/construction_ppe`; YOLO con splits oficiales train/val/test: 1132/143/141 imagenes. |

## Checklist por descarga

- Registrar URL exacta y fecha.
- Registrar version si la fuente la publica.
- Registrar tamano total del archivo o carpeta.
- Calcular hash SHA256 de archivos comprimidos cuando existan.
- Verificar que imagenes abren correctamente.
- Verificar que anotaciones son parseables.
- Registrar formato original real.
- Actualizar `datasets_metadata.yaml`.

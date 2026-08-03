# License Registry

Registro operativo de licencias, permisos de uso y restricciones de redistribucion.

| Dataset | Fuente | Licencia declarada | Estado | Notas |
|---|---|---|---|---|
| construction_site_safety | https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety | CC BY 4.0 | Aprobado | Verificada en Roboflow Universe. Habilitado para TRAIN y BENCH. Permite uso académico y redistribución con atribución. |
| ppe_siabar | https://universe.roboflow.com/siabar/ppe-dataset-for-workplace-safety | CC BY 4.0 | Aprobado | Verificada en Roboflow Universe. Habilitado para TRAIN. Permite uso académico y redistribución con atribución. |
| construction_safety_hardhat | https://www.kaggle.com/datasets/muhammetzualli/construction-safety-image-classification-system | CC0 (Public Domain) | No disponible | URL inválida al 2026-06-18. Dataset descartado del pipeline v2. |
| SH17 | https://github.com/ahmadmughees/SH17dataset | CC BY-NC-SA 4.0 | Verificada en README | Dataset completo descargado desde Kaggle; respetar uso no comercial y share-alike. |
| SHEL5K | https://data.mendeley.com/datasets/9rcv8mm682/4 | CC BY 4.0 | Aprobado | Verificada en pagina Mendeley. Version 4 / DOI 10.17632/9rcv8mm682.4; atribucion obligatoria. |
| CHV | https://github.com/ZijianWang-ZW/PPE_detection | Grant informal de los autores ("open for free use") + cita; SIN licencia formal (SPDX: none) | Aprobado (uso academico/evaluacion, SIN redistribucion de imagenes) | Verificacion 2026-07-29, ver seccion abajo. Cita obligatoria: wang2021ppe. Cumplimos la restriccion por construccion: imagenes raw gitignoradas, solo se versionan anotaciones derivadas en bench_v3.json. |
| Construction-PPE | https://docs.ultralytics.com/datasets/detect/construction-ppe/ | AGPL-3.0 | Verificada localmente | Archivo `LICENSE` incluido en descarga; documentar implicancias antes de redistribucion. |
| GDUT-HWD | https://github.com/wujixiu/helmet-detection | Verificar | Pendiente | Confirmar licencia y restricciones de Drive/Baidu. |
| SHWD | https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset | Verificar | Pendiente | Confirmar licencia y permisos de redistribucion. |
| SODA | https://linjiarui.net/en/portfolio/2022-02-22-SODA-site-object-detection-dataset-for-deep-learning-in-construction | Verificar | Pendiente | Mantener como extension contextual. |
| Pictor-PPE | https://github.com/ciber-lab/pictor-ppe | Verificar | Bloqueado | No usar antes de confirmar licencia efectiva y version. |
| MOCS | https://www.anlab340.com/Archives/IndexArctype/index/t_id/17.html | Verificar | Bloqueado | Puede requerir solicitud o validacion manual de acceso. |

## Criterio de uso

- `Pendiente`: se puede preparar estructura, pero no entrenar/evaluar hasta completar verificacion.
- `Aprobado`: licencia y fuente documentadas; dataset habilitado para el alcance registrado.
- `Bloqueado`: requiere permiso, acceso o aclaracion antes de incorporarse al corpus.

(Los estados historicos "Verificada en ..." se normalizaron a este vocabulario el
2026-07-29; la evidencia de verificacion quedo en la columna Notas.)

## Verificacion CHV (2026-07-29)

Evidencia recolectada contra la fuente:

- **GitHub API** (`GET /repos/ZijianWang-ZW/PPE_detection`): `license: None`; raiz del
  repo = `README.md` + `figures/` — **no existe archivo LICENSE** (repo activo,
  `updated_at: 2026-07-25`).
- **README (verbatim)**: *"The dataset is open for free use, please download at
  [Google Drive] or [Baidu Yunpan]"* y *"If the dataset helpes you, please cite the
  repository in your article: `@Article{wang2021ppe, AUTHOR = {Wang, Zijian and Wu,
  Yimin and Yang, Lichao and Thirunavukarasu, Arjun and Evison, Colin and Zhao,
  Yifan}, ...}`"*.

Lectura y declaracion para la tesis:

1. El **uso academico/evaluativo esta permitido explicitamente** por los autores
   ("open for free use"), con **cita obligatoria** (`wang2021ppe` — incluirla en la
   bibliografia de la tesis).
2. **No hay otorgamiento formal de redistribucion** (sin LICENSE, sin SPDX). Politica
   adoptada: **no redistribuir las imagenes** — ya se cumple por construccion (raw
   gitignorado; `bench_v3.json` versiona solo anotaciones derivadas y filenames).
3. En el informe de tesis, declarar el estrato `chv` como *"dataset academico de
   terceros usado para evaluacion bajo el grant de uso libre de sus autores, con
   cita; imagenes no redistribuidas"*.

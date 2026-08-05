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
| MOCS (copia Roboflow `mocs-bowib`) | https://universe.roboflow.com/mocs/mocs-bowib | CC BY 4.0 **declarada por el uploader de la copia** (original anlab340: sin verificar) | Aprobado (uso evaluativo, SIN redistribución) | ✎ 2026-08-05: lo que está en disco es la copia Roboflow (1.471 imgs, solo `Worker`), usada en el piloto A1 (doc 94, evidencia cualitativa + ancla person↔Worker). El original de anlab340 nunca se descargó. Para el informe: citar el paper original de MOCS + declarar la procedencia de la copia; imágenes no se redistribuyen (raw gitignorado). |
| ppe-dataset (rbyz "PPE 6 classes" v6) | https://universe.roboflow.com/rbyz/ppe-6-classes-ntld9 | MIT | Rechazado (S0) | Candidato a BENCH rechazado 2026-07-23 por calidad/dominio/integridad — 4 descalificadores, ver `evaluation_ppe_dataset.md`. La licencia no fue el problema. Raw (1,2 GB) borrable y re-descargable. |

## Material de VIDEO (agregado 2026-08-05)

Hasta hoy esta tabla solo cubria datasets de imagenes. El material de video —que es el
que sostiene el **resultado principal** de la tesis— no tenia ninguna entrada, contra lo
que exige **spec 43 §7 "Marco legal"**. Se registra aca.

**Los dos casos son distintos y conviene no mezclarlos:** el **rodaje** es material propio
en el que los grabados son los propios integrantes del proyecto (resuelto por declaracion,
sin terceros involucrados); el **lote de internet** es material de terceros con personas
identificables, y ahi el cuidado es real (ver las salvedades y los caveats mas abajo).

| Material | Origen | Uso en la tesis | Licencia / base de uso | Estado |
|---|---|---|---|---|
| **Rodaje propio 2026-07-25** (Bloque A) — 34 clips del banco, 35 episodios | grabacion propia con OAK-D Pro PoE + camara IP; participantes: integrantes del proyecto, actuando segun guion (doc 69: ACTOR A / ACTOR B) | **El banco de medicion**: las 12 campanas de Nivel B (T1/T2/G1/D1/H1/B1 + R1–R6) | Material propio. **Las personas que aparecen en cuadro son los propios integrantes del proyecto**, actuando segun el guion del doc 69: son a la vez los sujetos y los responsables del material, y **no hay terceros en cuadro**. Las situaciones son **actuadas**, no documentan conducta laboral real de nadie | ✅ **Resuelto por declaracion (usuario, 2026-08-05).** Lo administrativo lo maneja el equipo por su cuenta y la identificacion del responsable va **en el informe**, no en este registro. Queda disponible por si la facultad lo pide: [`plantilla-consentimiento-audiovisual.md`](plantilla-consentimiento-audiovisual.md) |
| **Lote de internet** (Bloque B) — 14 clips (`v01_c01`…`v10_c01`) de 10 videos fuente (`raw/1.1.mp4`…`10.1.mp4`) | **Canal de YouTube `@HospitalConstruction`** — https://www.youtube.com/@HospitalConstruction. Serie de seguimiento de la construccion de un hospital; el material usado son las subidas de *footage* a velocidad original (no los time-lapse de la serie). Ejemplo verificado: subido 2015-04-05, grabado 2015-03-28 | Validez externa: obra real no guionada, en cumplimiento (13× `P5`, 1× `P8`). **Levanta L4.** Sin GT todavia (en CVAT) | **Uso academico/evaluativo con cita, SIN redistribucion** (NO es un otorgamiento de licencia — ver Salvedad 1). Se cita el canal como fuente de las escenas. Se cumple por construccion: los `.mp4` estan gitignorados; solo se versionan anotaciones derivadas, previews y nombres de archivo | **Aprobado**, con 1 salvedad de encuadre + 2 caveats metodologicos (abajo) |
| `cb_b01_p7` (retirado) | obra real, Bloque B | ninguno — retirado del banco 2026-08-03 | sin registrar | **Retirado**: motivo #1 licencia/consentimiento sin registrar + GT por IA. Ver `processed/clip_bench/_retired/cb_b01_p7/MOTIVO.md` |

### Lote de internet — declaracion para el informe y las dos salvedades

**Declaracion (texto para el informe):** *"Las escenas de obra real no guionada provienen
del canal publico de YouTube `@HospitalConstruction`, citado como fuente. El material se
usa con fines academicos y de evaluacion; los videos no se redistribuyen: el repositorio
versiona unicamente anotaciones derivadas, previsualizaciones de baja resolucion y
nombres de archivo."* Es la misma postura ya adoptada y documentada para el estrato `chv`.

**Salvedad 1 (RESUELTA 2026-08-05, y define como se redacta) — es *Standard YouTube
License*, no Creative Commons.** Se reviso la descripcion de los videos: **no hay marcador
de Creative Commons**, asi que rige la licencia por defecto de YouTube, que **no** concede
derechos de reproduccion ni de obra derivada. La descripcion si declara que *"esta
grabacion es de vistas y escenas visibles al publico"* — pero eso es una afirmacion sobre
**que se filmo** (escenas visibles desde el espacio publico), **no un otorgamiento de
reuso**. No confundir las dos cosas al redactar.

**Consecuencia, que es la que hay que escribir:** el material se declara como **uso
academico/evaluativo con cita y sin redistribucion** — exactamente la misma postura ya
documentada para `chv` (dataset de terceros sin licencia formal). **Nunca** presentarlo
como "licencia CC" ni como "material de libre uso".

**Salvedad 2 — personas identificables de terceros.** Es obra real con operarios
identificables y **el consentimiento no es obtenible** (no son participantes del
proyecto). **La declaracion del autor ayuda acá, no en la licencia:** al afirmar que son
vistas y escenas visibles al publico, respalda que no hay expectativa razonable de
privacidad sobre lo filmado. Mitigaciones vigentes de todos modos: no se redistribuye el
material, no se guardan datos personales en el repo (spec 43 §7, minimizacion DA-08/09), y
no hay captura automatica en runtime (E-11 intacta). **Regla operativa:** si un frame del
lote de internet se publica como figura del informe, **se difuminan las caras**. Para el
rodaje propio no aplica (hay consentimiento, una vez firmado).

### Caveats metodologicos del estrato (2026-08-05)

Dos cosas que salieron de leer la descripcion del autor y que **van declaradas junto al
estrato**, porque afectan como se lee su resultado:

1. **Velocidad real, verificada por dos vias — las metricas temporales SI aplican.** El
   canal publica sobre todo **time-lapse**; lo que se uso son las subidas a velocidad
   original. Si un clip viniera de un time-lapse, TTFD / `confirm_after_ms` / SDR serian
   inservibles (el tiempo de video no seria tiempo real). Verificado: (a) el autor lo
   declara explicitamente, y (b) **medido** sobre las pre-anotaciones de los 14 clips — el
   desplazamiento de las cajas es de **0,4–2,8 px/frame de mediana** (max ~23), propio de
   movimiento continuo a 30 fps; un time-lapse daria saltos de decenas o cientos de px.
   Los 14 masters son **1920×1080 @ 30 fps**.
2. **El material NO es camara-nativo.** El autor declara que la imagen fue
   **corregida de color y estabilizada**, y que recorto tramos (camara al piso/cielo,
   movimientos bruscos). Para un banco de percepcion es un preproceso ajeno que no
   controlamos: se declara. No invalida nada — el rodaje propio si es camara-nativo, asi
   que los dos estratos se leen por separado (regla L5).

**Pendiente de completar aca:** la URL de cada video fuente y su fecha de acceso, por
master `raw/N.M.mp4`. Hoy esta registrado el canal y la referencia de un video
(subido 2015-04-05, grabado 2015-03-28).

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

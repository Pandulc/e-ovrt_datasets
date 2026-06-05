# E-OVRT-VDP

**Experimental Open-Vocabulary Real-Time Video Detection Platform**

Repositorio dedicado a la implementacion de la plataforma experimental de deteccion open-vocabulary en video en tiempo real para monitoreo asistivo de riesgos en construccion civil.

## Contexto del proyecto

E-OVRT-VDP es un Proyecto Integrador de Ingenieria en Informatica del Centro Regional Universitario Cordoba IUA. El trabajo aborda la seguridad laboral en construccion civil desde una perspectiva experimental: no busca reemplazar la supervision humana ni emitir determinaciones normativas automaticas, sino evaluar si modelos vision-lenguaje y deteccion open-vocabulary pueden asistir la identificacion de indicios visuales de riesgo en video.

El problema central es la brecha entre entornos de obra dinamicos, semanticamente abiertos y dependientes del contexto, y sistemas de deteccion visual tradicionales basados en vocabularios cerrados. En una obra, condiciones como `persona sin casco`, `persona sin chaleco reflectivo` o `maquinaria cerca de peatones` combinan objetos, atributos, relaciones espaciales, persistencia temporal y contexto operativo. Por eso, el proyecto propone una plataforma experimental capaz de procesar video, interpretar consultas o prompts, producir detecciones, evaluar patrones de riesgo, registrar eventos y generar alertas asistivas trazables.

## Objetivo

Disenar, implementar y evaluar la factibilidad tecnica de una plataforma experimental de deteccion open-vocabulary en video en tiempo real, orientada a la identificacion asistiva de condiciones de riesgo en obras de construccion civil, integrando:

- modelos vision-lenguaje y deteccion open-vocabulary;
- procesamiento de video de baja latencia;
- seguimiento temporal cuando corresponda;
- patrones de riesgo observables;
- registro de eventos y trazabilidad experimental;
- mecanismos de alerta evaluables bajo condiciones controladas.

## Alcance del repositorio

Este repositorio alojara la implementacion de la plataforma E-OVRT-VDP y los artefactos necesarios para reproducir la etapa experimental. Actualmente contiene la primera base de trabajo sobre datasets:

- obtencion y registro de datasets prioritarios;
- validacion basica de imagenes y anotaciones;
- conversion a formatos COCO, YOLO y ODVG;
- documentacion operativa del avance;
- scripts de descarga, validacion y conversion.

La implementacion futura de la plataforma deberia crecer alrededor de modulos de ingesta de video, inferencia open-vocabulary, tracking, evaluacion de patrones, eventos, alertas, metricas y APIs de prueba.

## Estado actual

Los cuatro datasets prioritarios iniciales fueron descargados, validados a nivel basico y convertidos a COCO, YOLO y ODVG:

| Dataset | Estado | Formatos generados |
|---|---|---|
| SH17 | Descargado y validado | COCO, YOLO, ODVG |
| SHEL5K | Descargado y validado | COCO, YOLO, ODVG |
| CHV | Descargado y validado | COCO, YOLO, ODVG |
| Construction-PPE | Descargado y validado | COCO, YOLO, ODVG |

Se generaron dos vistas por dataset:

- `original`: conserva las clases originales.
- `canonical_cr01_cr02`: normaliza a `person`, `helmet`, `vest`, `no_helmet`, `no_vest` para las condiciones iniciales CR-01 y CR-02.

## Estructura principal

```text
datasets/
  documentation/        # Documentacion del plan, procedimientos y avance
  registry/             # Metadata, licencias, logs y reportes legibles
  raw/                  # Datasets crudos locales; imagenes/ZIPs no se versionan
  processed/            # Salidas COCO, YOLO, ODVG y reportes JSON
  scripts/              # Scripts de descarga, validacion y conversion
  splits/               # Manifiestos de particion y futuros splits congelados
```

## Politica de versionado de datos

El repositorio no debe subir imagenes crudas, videos crudos ni archivos comprimidos de datasets. Esos artefactos quedan excluidos por `.gitignore` dentro de `datasets/raw/`.

Si se versionan:

- documentacion;
- scripts;
- registros de metadata/licencias/descarga;
- anotaciones y metadata no multimedia cuando corresponda;
- salidas procesadas necesarias para reproducibilidad experimental.

## Documentacion disponible

- `datasets/documentation/README.md`
- `datasets/documentation/procedimientos_realizados.md`
- `datasets/documentation/estado_avance.md`
- `datasets/documentation/guia_conversiones.md`
- `datasets/documentation/plan_obtencion_preparacion_datasets_e_ovrt_vdp.md`
- `datasets/registry/conversion_report.md`

## Conversion de datasets

Para regenerar las conversiones:

```bash
datasets/scripts/convert/convert_datasets.py --datasets chv shel5k construction_ppe sh17
```

Salidas:

```text
datasets/processed/coco/{view}/{dataset_id}/{split}.json
datasets/processed/yolo/{view}/{dataset_id}/
datasets/processed/odvg/{view}/{dataset_id}/{split}.jsonl
```

## Remoto

Repositorio remoto configurado:

```text
https://github.com/Pandulc/E-OVRT-VDP.git
```

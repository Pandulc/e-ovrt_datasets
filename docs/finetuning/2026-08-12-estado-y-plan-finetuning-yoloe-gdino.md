# Estado y plan de continuidad del fine-tuning YOLOE/GDINO

- **Fecha del relevamiento:** 2026-08-12.
- **Alcance:** estado de datos, modelos, scripts, evaluacion, entorno y cluster necesarios
  para ajustar un modelo de la familia YOLOE y uno de la familia Grounding DINO.
- **Estado general:** preparacion avanzada para YOLOE T1, preparacion insuficiente para
  GDINO/MM-GDINO y cluster temporalmente sin nodos libres visibles.
- **Naturaleza del documento:** fotografia operativa y hoja de ruta. No registra una
  corrida de entrenamiento ni reemplaza los criterios experimentales ya aprobados.

## 1. Proposito

Este documento concentra el relevamiento necesario para responder, sin tener que recorrer
varios repositorios, estas preguntas:

1. Que activos estan realmente disponibles para hacer fine-tuning.
2. Que parte del camino YOLOE ya fue ejercida y que parte solo esta documentada.
3. Que significa "entrenar GDINO" en este proyecto y por que hay dos caminos distintos.
4. Que bloquea hoy una corrida en Mendieta.
5. Que decisiones deben tomarse antes de consumir GPU.
6. En que orden conviene continuar para preservar el protocolo y la reproducibilidad.

La conclusion corta es que **no corresponde lanzar hoy los dos entrenamientos**. El camino
YOLOE-26s/T1 tiene un loop ejercido mediante smoke y un costo medido, pero todavia necesita
una decision metodologica, portabilidad y un puente de evaluacion. Para GDINO hay datos y
pesos base, pero no existe aun un pipeline ejecutable e integrado.

## 2. Semaforo ejecutivo

| Frente | Estado | Lectura operativa |
|---|---|---|
| YOLOE-26s, linear probing T1 | **Amarillo** | Trainer y smoke disponibles; no lanzar hasta cerrar F-100.1, portabilidad e integracion |
| YOLOE full fine-tuning T2 | **Rojo condicionado** | Solo se habilita si T1 cumple el go/no-go |
| Grounding DINO original, IDEA Research | **Rojo** | Pesos y serving disponibles; no hay trainer ni receta local |
| MM-Grounding-DINO tiny, T3 | **Rojo** | ODVG disponible, pero faltan stack, config, smoke y puente de checkpoint; existe ademas un antecedente de bboxes defectuosas |
| Datos de entrenamiento permitidos | **Verde** | CSS + PPE Siabar, 3.723 train, licencias compatibles con transporte al cluster |
| Evaluacion congelada | **Verde parcial** | `bench_v3` existe y esta congelado; falta integrar los checkpoints ajustados |
| Mendieta | **Amarillo** | Conexion sin limite practico y asignacion multi-nodo amplia; cada job tiene un walltime maximo de 2 dias y falta preparar el entorno |

## 3. Documentos que gobiernan el estado

Cuando dos documentos parezcan discrepar debe usarse este orden de precedencia:

1. [ADR-017](../../../docs/decisiones/adr-017-fine-tuning-jornada-experimental.md):
   E-04 es una jornada experimental comprometida; no se encuadra como descarte por tiempo.
2. [Documento 100](../../../docs/operacion/100-t1-dimensionamiento-medido.md):
   contiene el smoke real, la enmienda anti-leakage y la checklist tecnica vigente para T1.
3. [Plan E-04](../../../docs/contingencia/20-investigacion-finetuning-condicionada-e04.md):
   define la escalera T1-T2-T3 y sus go/no-go.
4. [Seleccion S1/S2](../../../docs/operacion/64-resultados-s1-s2-seleccion-modelos.md):
   registra el comportamiento medido de las variantes, incluido el descarte de MM-GDINO.
5. [Registro de `bench_v3`](../../datasets/registry/bench_v3.md) y
   [registro de licencias](../../datasets/registry/license_registry.md):
   gobiernan evaluacion, congelamiento, uso y transporte de datos.

Dos correcciones son particularmente importantes:

- El plan E-04 original habla de 5.540 imagenes de `train_v2`. El conjunto efectivo para
  T1 ya no es ese: el documento 100 excluye CHV y SHEL5K por leakage contra `bench_v3`.
- El plan propone MM-GDINO-tiny para T3, pero los resultados posteriores registran bboxes
  degeneradas en tiny y el descarte empirico de la familia. T3 no puede ignorar ese hecho.

## 4. Estado de los datos

### 4.1 Contrato canonico

El vocabulario activo de `canonical_v2` es:

| Id | Clase | Observacion |
|---:|---|---|
| 0 | `person` | Persona/cuerpo visible |
| 1 | `helmet` | Casco como objeto |
| 2 | `vest` | Chaleco reflectivo/de seguridad |
| 3 | `bare_head` | Cabeza descubierta; solo desde negativo explicito |

El contrato completo esta en
[`annotation_contract_v2.yaml`](../../datasets/registry/annotation_contract_v2.yaml).
No debe inferirse `bare_head` por ausencia de casco ni tratar una clase no exhaustiva como
negativo.

### 4.2 Conjunto efectivo para YOLOE T1

El arbol preparado por el smoke usa:

| Fuente | Split | Rol | Imagenes |
|---|---|---|---:|
| `construction_site_safety` | train | train | 2.603 |
| `ppe_siabar` | train | train | 1.120 |
| `ppe_siabar` | val | monitor | 326 |
| **Total train** | | | **3.723** |

No se usa CHV porque todo CHV integra `bench_v3`. Tampoco se usa SHEL5K porque es el
estrato que aporta la mayor parte de `bare_head` al bench congelado. La interseccion del
train efectivo con `bench_v3` fue documentada como cero por basename y stem.

### 4.3 Formatos disponibles

- **YOLO:** `datasets/processed/yolo/canonical_v2/<fuente>/`.
- **ODVG:** `datasets/processed/odvg/canonical_v2/<fuente>/`.
- **COCO:** `datasets/processed/coco/canonical_v2/<fuente>/`.
- **Evaluacion:** `datasets/processed/coco/bench/curated/bench_v3.json`.

Los `data.yaml` YOLO por fuente no constituyen por si solos el dataset combinado de T1.
El preparador T1 genera un arbol nuevo con imagenes y labels emparejadas y su propio
`data.yaml`.

### 4.4 Trampa de labels ya resuelta localmente

Las listas de imagenes de `canonical_v2` apuntan a imagenes bajo `raw/`. Ultralytics deriva
la label reemplazando `/images/` por `/labels/`; para CSS y PPE esa ruta puede resolver a
labels originales de Roboflow con otro vocabulario. Entrenar directamente contra esas
listas puede usar clases equivocadas sin fallar.

El script
[`100-t1-preparar-datos.py`](../../../docs/operacion/datos/100-t1-preparar-datos.py)
resuelve la trampa creando un arbol `images/` + `labels/` que enlaza imagenes raw con labels
canonicas. Tambien controla ids de clase, stems unicos y conteos exactos.

### 4.5 Licencias y payload

Los datos que pueden viajar a Mendieta son:

- `construction_site_safety`: CC BY 4.0.
- `ppe_siabar`: CC BY 4.0.

El volumen local relevado es aproximadamente:

| Pieza | Tamano aproximado |
|---|---:|
| CSS raw | 314 MB |
| PPE Siabar raw | 205 MB |
| Labels canonicas CSS | 11 MB |
| Labels canonicas PPE | 6,5 MB |
| **Payload T1 antes de empaquetar** | **aprox. 537 MB** |

CHV no debe salir de la maquina por su permiso informal sin licencia formal de
redistribucion. El principio operativo sigue siendo: **entrenar en el cluster, evaluar
localmente**.

## 5. YOLOE: estado detallado

### 5.1 Variante preparada

El camino ejercido es **YOLOE-26s detection con linear probing**. Aunque el plan general
menciona `26s/m`, el script existente implementa solamente `26s`.

Punto de partida:

- Config de deteccion: `yoloe-26s.yaml` provista por Ultralytics.
- Pesos iniciales: `models/yoloe/original/yoloe-26s-seg.pt`.
- Trainer: `YOLOEPETrainer`.
- Epocas T1: 10.
- Resolucion: 640.
- Seed: 100.
- Determinismo: habilitado.
- Defaults conservadores: `batch=8`, `workers=2`.

La inicializacion desde YAML de deteccion y carga posterior del checkpoint segmentado sigue
el procedimiento oficial de Ultralytics para entrenar detection con pesos YOLOE de
segmentacion.

### 5.2 Lo que ya fue ejercido

El script
[`100-t1-entrenar-lp.py`](../../../docs/operacion/datos/100-t1-entrenar-lp.py)
se uso en un smoke de:

- 1 epoca.
- `fraction=0.05`.
- 186 imagenes.
- 24 batches de 8.
- Validacion sobre las 326 imagenes de PPE Siabar val.

El documento 100 registra `rc=0`, entre 2,42 y 2,61 GB de VRAM y aproximadamente 16 s de
train para la epoca reducida. La extrapolacion documentada para 3.723 imagenes por 10
epocas es aproximadamente una hora en RTX 4060 y una cota conservadora de menos de
1 GPU-h en A30.

Esto demuestra que el loop local corre. No demuestra todavia que T1 completo mejore las
metricas ni que el checkpoint producido se integre correctamente al servicio.

### 5.3 F-100.1: decision bloqueante

El monitor `ppe_siabar val` contiene `person`, `helmet` y `vest`, pero **cero instancias de
`bare_head`**. La clase si aparece en train, pero no puede observarse durante el
entrenamiento. Usar `best.pt` seleccionaria el checkpoint mediante una metrica que ignora
una de las clases centrales.

Las alternativas documentadas son:

1. Seleccionar `last.pt` en vez de `best.pt`.
2. Crear un val con `bare_head`, lo cual hoy obliga a tocar SHEL5K y romper el congelamiento
   de `bench_v3`.
3. Mantener el monitor actual y medir `bare_head` solo en la evaluacion final contra
   `bench_v3`, declarando la ceguera durante entrenamiento.

**Recomendacion operativa:** congelar las 10 epocas, seleccionar `last.pt`, usar PPE val
solo como monitor descriptivo y medir `bare_head` una unica vez en la evaluacion final.
Esta combinacion no modifica el bench ni permite usarlo para elegir hiperparametros. Debe
quedar aprobada y registrada antes de lanzar T1.

### 5.4 Bloqueos de portabilidad

Los scripts actuales no pueden copiarse y ejecutarse sin cambios en Mendieta:

- Fijan `/home/simonll4/projects/...` para datasets, pesos y destino.
- El preparador crea symlinks hacia rutas absolutas locales.
- El trainer copia el resultado al media-plane local.
- No existe un manifiesto portable de dependencias para entrenamiento.
- No existe imagen Apptainer ni `sbatch` versionado.

El bundle remoto debe materializar imagenes y labels, o transportar una estructura relativa
completa. No debe subir un arbol de symlinks que apunte de vuelta a esta maquina.

### 5.5 Bloqueo de serving y evaluacion

El trainer de probing precomputa embeddings para las cuatro clases, fusiona el head y
entrena sus proyecciones finales. En cambio, el
[`YOLOEUltralyticsAdapter`](../../../e-ovrt_media-plane/src/eovrt_media/models/yoloe_adapter.py)
del media-plane llama `set_classes()` cuando cambia el plan de prompts.

Por eso falta comprobar explicitamente:

1. Que el checkpoint T1 carga con `YOLOE(<peso>)`.
2. Que infiere correctamente con el vocabulario fijo y el mismo orden/string de clases.
3. Que no se intenta cambiar a un subconjunto incompatible con el head fusionado.
4. Que los ids producidos conservan el contrato `person/helmet/vest/bare_head`.
5. Que puede registrarse en `configs/models/yoloe/` y ejecutarse contra `bench_v3`.

Congelar el backbone preserva sus parametros preentrenados, pero eso no prueba por si solo
la capacidad funcional de cambiar vocabulario en el artefacto fusionado. La sonda
generalista o de clase nueva debe ejercerse sobre el checkpoint final, no inferirse de la
cantidad de parametros congelados.

### 5.6 Definicion de "T1 listo para pedir GPU"

T1 queda listo solo cuando se cumpla todo esto:

- [ ] F-100.1 decidida y reflejada en el trainer.
- [ ] Rutas parametrizables; ninguna ruta personal hardcodeada.
- [ ] Payload materializado y atribuible, sin symlinks rotos.
- [ ] Dependencias congeladas en una imagen Apptainer reproducible.
- [ ] Job Slurm con recursos, logs, timeout y directorio de salida explicitos.
- [ ] Smoke de carga/inferencia del checkpoint en el media-plane preparado.
- [ ] Catalogo y manifest de evaluacion del modelo ajustado preparados.
- [ ] Comando de evaluacion contra el `bench_v3` congelado preparado.
- [ ] Registro previsto para pesos, metricas, costo y logs.

## 6. GDINO: dos caminos que no deben confundirse

### 6.1 Grounding DINO original de IDEA Research

Los checkpoints `grounding-dino-tiny` y `grounding-dino-base` estan disponibles localmente
en layout Hugging Face. El media-plane los consume mediante
[`GroundingDinoHFAdapter`](../../../e-ovrt_media-plane/src/eovrt_media/models/grounding_dino_adapter.py),
que usa `AutoProcessor` y `AutoModelForZeroShotObjectDetection.from_pretrained()`.

Ese camino es hoy **serving, no training**. No existe en los repos:

- trainer para el checkpoint original;
- dataset/collator integrado con Transformers;
- receta de fine-tuning;
- smoke de backward/optimizer;
- job Slurm;
- export e integracion de un checkpoint ajustado.

Elegir estrictamente "Grounding DINO original" implica abrir una rama nueva de ingenieria
y experimentacion, no completar una receta ya preparada.

### 6.2 MM-Grounding-DINO de MMDetection

El plan T3 elige **MM-GDINO-tiny open-vocabulary fine-tuning** porque MMDetection ofrece
un stack de entrenamiento publico para la familia. Los exports ODVG locales reducen parte
del trabajo de datos, pero no vuelven ejecutable el entrenamiento.

Falta actualmente:

- checkout/pin de MMDetection;
- `mmdet`, `mmcv`, `mmengine` y `pycocotools`;
- checkpoint base en el formato esperado por el trainer MMDetection;
- config derivada del recipe oficial;
- plan distribuido para la cantidad de nodos/GPU solicitada;
- definicion de batch global, batch por GPU, acumulacion y escalado de learning rate;
- early stopping y evaluacion por epoca sin tocar `bench_v3`;
- smoke de entrenamiento;
- script Slurm;
- conversion del `.pth` final a Hugging Face o un adapter MMDetection nuevo.

Los checkpoints MM-GDINO que existen en el media-plane estan en layout Hugging Face
(`model.safetensors`). No debe asumirse que son entrada directa del trainer MMDetection ni
que un `.pth` producido por este puede cargarse con `from_pretrained()`.

### 6.3 Bloqueo previo: antecedente de bboxes degeneradas

La variante tiny fue excluida previamente por cajas degeneradas. MM-GDINO-large reprodujo
el defecto y base no mostro una ventaja que justificara mantener la familia en la
seleccion. Antes de entrenar debe determinarse si el problema estaba en:

- checkpoint o conversion Hugging Face;
- processor/postproceso;
- escalado de cajas;
- adapter compartido;
- variante concreta.

No se debe gastar una corrida de fine-tuning para intentar compensar un error de
integracion. Primero hace falta una baseline zero-shot geometricamente valida.

### 6.4 Baseline comparable

El efecto de fine-tuning solo puede medirse comparando el checkpoint ajustado contra **el
mismo checkpoint base**, con el mismo preprocesamiento, resolucion, prompts y evaluador.

No seria metodologicamente valido comparar:

- baseline `IDEA-Research/grounding-dino-tiny`, contra
- fine-tune iniciado desde otro pretraining de MM-GDINO.

Eso mezcla cambio de linaje con efecto de entrenamiento. Si se elige MM-GDINO, primero hay
que obtener y congelar su baseline sana en `bench_v3`.

### 6.5 Datos para T3

Los ODVG disponibles contienen rutas relativas a `datasets/raw/...`, lo que favorece la
portabilidad si se conserva la raiz del repo. Sin embargo, T3 debe aplicar la misma regla
anti-leakage que T1: entrenar con CSS + PPE Siabar, no con las 5.540 imagenes completas que
incluyen CHV.

Tambien debe decidirse un monitor que no use `bench_v3`. La carencia de `bare_head` en
PPE val no desaparece por cambiar de arquitectura.

### 6.6 Secuencia protocolar

La escalera pre-registrada es:

1. **T1:** YOLOE-26s linear probing.
2. **T2:** YOLOE full fine-tuning, solo si T1 cumple la ganancia exigible.
3. **T3:** MM-GDINO open-vocabulary, solo si T2 sostiene el resultado y la logistica lo
   permite.

Por lo tanto, pedir "un YOLOE y un GDINO" como dos corridas independientes o paralelas
requiere primero decidir si se mantiene esta escalera o si se enmienda el protocolo. Sin
esa decision, el estado vigente no habilita T3 antes de T1/T2.

### 6.7 Definicion de "T3 listo para pedir GPU"

- [ ] Elegido explicitamente GDINO original o MM-GDINO.
- [ ] Resuelto el antecedente de bboxes degeneradas.
- [ ] Baseline valida del checkpoint exacto congelada.
- [ ] Dataset ODVG anti-leakage y monitor definidos.
- [ ] Stack MMDetection o trainer alternativo pinneado.
- [ ] Checkpoint de partida compatible con el trainer.
- [ ] Config distribuida y regla de escalado de batch/LR justificadas.
- [ ] Smoke de backward, validacion y guardado completado.
- [ ] Formato de salida y puente al media-plane definidos.
- [ ] T1/T2 habilitaron T3 o existe una enmienda explicita del protocolo.

## 7. Estado de Mendieta al 2026-08-12

La inspeccion remota fue de solo lectura y representa una fotografia temporal.

### 7.1 Slurm y capacidad

- Cluster accesible con la cuenta del proyecto bajo la asociacion `iua`.
- 19 nodos visibles en las particiones `short` y `multi`.
- 20 CPU, aproximadamente 64 GB RAM y 2 recursos GPU por nodo.
- 38 GPU configuradas en Slurm en total.
- `short`: limite de 1 hora.
- `multi`: limite de 48 horas.
- Estado observado: 3 nodos `alloc`, 16 `drng`, cero nodos `idle`.
- No habia jobs propios en cola o ejecucion.

La restriccion operativa debe leerse correctamente:

- **El tiempo de conexion no es el limite.** Se puede mantener el acceso y preparar datos,
  contenedores, configs y jobs sin consumir el presupuesto de entrenamiento.
- **El limite es el walltime de cada corrida Slurm:** como maximo 2 dias en `multi`.
- **La cantidad de nodos no es la restriccion principal.** Se pueden solicitar varios
  nodos en una misma corrida; por ejemplo, 8 nodos con 2 GPU cada uno, es decir 16 GPU,
  durante esas 48 horas.
- La fotografia sin nodos `idle` solo describe el estado instantaneo del scheduler al
  relevarlo. No significa que el proyecto tenga un cupo fijo de una GPU ni que deba
  redisenarse todo para single-GPU.

El alcance de este documento es **Mendieta**. Las asociaciones que puedan aparecer para
otros clusters o grupos de nodos no deben incorporarse al plan salvo una decision
explicita posterior.

La documentacion del proyecto identifica las GPU como A30 de 24 GB. Slurm solo expuso
`gpu:2`, sin modelo. Como no habia asignacion no pudo confirmarse el hardware mediante
`nvidia-smi` en un compute node. Esa comprobacion debe hacerse dentro del primer job.

### 7.2 Entorno remoto

En el login se observo:

- Python 3.6 del sistema.
- Sin Python moderno, Conda, Mamba o `uv`.
- Sin modulo Python o CUDA visible mediante Lmod.
- Sin checkout del proyecto ni entorno de entrenamiento en `$HOME`.
- Apptainer/Singularity y Podman disponibles.
- Filesystem compartido con capacidad general amplia; la cuota especifica del usuario no
  quedo informada por `quota`.

La conclusion es que **Apptainer es el camino recomendado**. Instalar directamente sobre
Python 3.6 o depender de paquetes del login no es reproducible ni compatible con el entorno
local actual. El contenedor y los datos pueden prepararse durante tiempo de conexion; el
walltime limitado empieza a importar al someter la corrida de entrenamiento.

### 7.3 Estrategia de ejecucion recomendada

1. Construir y probar la definicion de contenedor fuera del turno GPU.
2. Transferir una imagen `.sif` o construirla en una particion permitida, segun politica
   del sitio.
3. Transferir solo CSS, PPE Siabar, labels canonicas, configs y scripts.
4. Usar `short` para el smoke, no para T1 completo: la estimacion de una hora queda pegada
   al limite y no incluye I/O, cache o arranque.
5. Usar `multi` con margen para T1 completo. T1 es tan pequeno que una GPU probablemente
   sea mas eficiente que distribuirlo; disponer de muchos nodos no obliga a usarlos.
6. Para MM-GDINO, aprovechar que el recipe oficial ya presupone 8 GPU: puede solicitarse,
   por ejemplo, 4 nodos de 2 GPU. Pedir 8 nodos/16 GPU tambien es posible, pero obliga a
   redimensionar batch global y learning rate; duplicar GPU sin esa revision cambia el
   experimento y puede empeorar la optimizacion sobre solo 3.723 imagenes.
7. Toda corrida que pueda acercarse a 48 horas debe guardar checkpoints periodicos y poder
   reanudarse en un job posterior. No debe depender de una sesion ininterrumpida mayor al
   walltime permitido.
8. Registrar dentro del job GPU real, driver, CUDA, imagen, commit/config, topologia
   distribuida y paths.
9. Descargar pesos, logs y metricas; hacer la evaluacion final localmente.

No deben copiarse al repo o al cluster claves SSH, helpers locales, tokens ni credenciales.

## 8. Entorno local relevante

El entorno del media-plane relevado contiene:

| Paquete | Version/estado |
|---|---|
| Python | 3.12.13 |
| Ultralytics | 8.4.86 |
| PyTorch | 2.12.1 |
| Torchvision | 0.27.1 |
| Transformers | 5.12.1 |
| Accelerate | 1.14.0 |
| MMDetection | ausente |
| MMCV | ausente |
| MMEngine | ausente |
| pycocotools | ausente |

Los pesos base YOLOE s/m/l/x, GDINO tiny/base y MM-GDINO tiny/base/large estan cacheados.
Las carpetas `models/<familia>/finetuned/` solo contienen `.gitkeep`: no hay checkpoints
propios producidos.

## 9. Arquitectura operacional objetivo

El flujo reproducible debe ser:

```text
e-ovrt_datasets local
  -> seleccion anti-leakage + labels canonicas
  -> bundle materializado y manifiesto/hash
  -> transferencia del payload permitido
  -> Apptainer + Slurm en Mendieta
  -> checkpoint + args + metricas + logs
  -> descarga de artefactos
  -> catalogo de modelo en e-ovrt_media-plane
  -> inferencia local sobre bench_v3 congelado
  -> evaluacion, latencia y sonda de retencion/clase nueva
  -> decision go/no-go registrada
```

Cada corrida debe registrar como minimo:

- familia, variante y checkpoint base;
- version exacta del codigo/config;
- fuentes, splits, conteos y hashes del dataset;
- vocabulario y strings de prompt;
- seed y determinismo;
- hiperparametros completos;
- hardware, driver, CUDA y versiones de paquetes;
- recursos y tiempos de Slurm;
- checkpoint `last`/`best` y regla de seleccion;
- logs, metricas de train/val y errores;
- metrica final por clase y por estrato de `bench_v3`;
- latencia del checkpoint final;
- costo GPU-h real;
- resultado del go/no-go y causa.

## 10. Go/no-go vigente

Los criterios se fijan antes de observar resultados:

| Dimension | Criterio |
|---|---|
| Ganancia | Delta AP@0.5 >= +0,05 absoluto en clase objetivo, o recall de clase colapsada pasa de <0,1 a >0,5 |
| Retencion | Caida relativa <=10% en subset generalista cuando corresponda |
| Operacion | Sin degradacion inaceptable de latencia en el CPN |
| Integridad | Sin leakage, tuning contra `bench_v3` ni cambio post hoc de criterios |

Un resultado negativo se documenta con numeros y cierra la rama; no se corrigen umbrales
despues de ver el resultado.

## 11. Hoja de ruta recomendada

### Fase 0: cerrar decisiones

1. Aprobar la enmienda F-100.1.
2. Confirmar si "GDINO" significa el checkpoint original o MM-GDINO.
3. Confirmar si se conserva la escalera T1-T2-T3 o se desea una comparacion independiente
   de una variante por familia.
4. Si T2 se habilita, elegir antes el subset generalista de retencion.

### Fase 1: convertir T1 en kit portable

1. Parametrizar raiz de datasets, pesos, salida y cache.
2. Separar preparacion, entrenamiento, export e integracion.
3. Materializar el dataset de transporte y emitir manifiesto con conteos/hashes.
4. Pinnear dependencias en Apptainer.
5. Crear `sbatch` para smoke y corrida completa.
6. Preparar catalogo y manifest de evaluacion antes de entrenar.
7. Preparar smoke de serving para vocabulario fijo.

### Fase 2: smoke remoto T1

1. Esperar un nodo disponible.
2. Ejecutar en `short` una epoca/fraccion pequena.
3. Registrar GPU real, entorno, consumo, salida y checkpoint.
4. Descargar el checkpoint y ejercer el puente de serving local.
5. Corregir infraestructura antes de pedir la corrida completa; no tocar hiperparametros
   experimentales basandose en `bench_v3`.

### Fase 3: T1 completo

1. Ejecutar 10 epocas en `multi`.
2. Conservar `last.pt`, args, results, logs y costo.
3. Descargar artefactos y catalogar el peso.
4. Evaluar una sola vez contra `bench_v3`.
5. Medir por clase, por estrato, CR-01/CR-02 cuando aplique, latencia y sonda de clase
   nueva/generalista.
6. Aplicar el go/no-go sin renegociarlo.

### Fase 4: T2, solo si queda habilitado

1. Definir full fine-tuning y retencion antes de correr.
2. Preparar smoke separado: T1 no valida T2.
3. Entrenar, evaluar y documentar con el mismo principio train remoto/eval local.

### Fase 5: investigacion ejecutable GDINO

1. Resolver primero el bug de MM-GDINO y obtener baseline sana.
2. Elegir stack y checkpoint de partida exactos.
3. Preparar config single-GPU y ODVG anti-leakage.
4. Ejercer smoke de backward, val y checkpoint.
5. Resolver conversion/adapter antes de la corrida larga.
6. Lanzar T3 solo si el protocolo lo habilita.

## 12. Acciones que no deben realizarse

- No entrenar directamente con `splits/v2/train.txt` de 5.540 imagenes.
- No incluir CHV o SHEL5K en train si se evalua contra `bench_v3`.
- No subir CHV al cluster.
- No seleccionar hiperparametros o checkpoints mirando `bench_v3`.
- No copiar `best.pt` de T1 sin resolver F-100.1.
- No asumir que los symlinks locales sobreviviran al transporte.
- No asumir que el checkpoint T1 acepta prompts dinamicos sin un smoke de integracion.
- No asumir que `model.safetensors` de MM-GDINO entrena directamente en MMDetection.
- No entrenar MM-GDINO para compensar cajas rotas del adapter/checkpoint.
- No comparar un GDINO original zero-shot contra un MM-GDINO ajustado como si solo
  cambiara el fine-tuning.
- No asumir A30 o CUDA especifica hasta medir dentro de un job asignado.
- No lanzar jobs largos desde una shell SSH sin Slurm y logs persistentes.

## 13. Decisiones abiertas

| Id | Decision | Recomendacion actual | Bloquea |
|---|---|---|---|
| D-FT-01 | Regla F-100.1 | 10 epocas fijas, `last.pt`, monitor descriptivo y `bare_head` solo en eval final | T1 |
| D-FT-02 | Variante GDINO | No elegir hasta resolver bboxes; si es MM-GDINO, congelar baseline exacta | T3 |
| D-FT-03 | Escalera o dos ramas independientes | Mantener T1-T2-T3 salvo enmienda explicita | T3 |
| D-FT-04 | Retencion T2 | Elegir subset y metrica antes de entrenar | T2 |
| D-FT-05 | Formato de salida MM-GDINO | Conversion a HF o adapter MMDetection, decidido antes del smoke | T3 |
| D-FT-06 | Recursos distribuidos T3 | Partir del recipe de 8 GPU; aumentar hasta 16 solo con batch/LR y motivo registrados | T3 |

## 14. Fuentes tecnicas externas

- [Ultralytics YOLOE](https://docs.ultralytics.com/models/yoloe/): entrenamiento de
  detection e instance segmentation y uso de trainers dedicados.
- [Referencia `YOLOEPETrainer`](https://docs.ultralytics.com/reference/models/yolo/yoloe/train/):
  linear probing y capas entrenables.
- [MMDetection MM-Grounding-DINO](https://github.com/open-mmlab/mmdetection/blob/main/configs/mm_grounding_dino/README.md):
  implementacion y recipes publicos de entrenamiento.
- [MM-GDINO usage](https://github.com/open-mmlab/mmdetection/blob/main/configs/mm_grounding_dino/usage.md):
  formatos y comandos de referencia.
- [Transformers Grounding DINO](https://huggingface.co/docs/transformers/model_doc/grounding-dino):
  contrato del modelo que consume el adapter actual.

## 15. Proximo hito concreto

El proximo hito no es "entrenar ambos modelos". Es:

> **Cerrar D-FT-01 y producir un kit T1 portable que pueda completar un smoke en
> Mendieta y cuyo checkpoint pueda evaluarse localmente sin tocar el bench durante
> entrenamiento.**

Una vez que ese circuito completo funcione, el proyecto tendra una plantilla real para
evaluar T2 y para diseñar T3 con evidencia, en vez de trasladar al camino GDINO supuestos
que hoy no estan verificados.

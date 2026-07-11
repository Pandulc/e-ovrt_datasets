# Guía operativa — corrección en CVAT (etapa 2 del video-gt-lab)

Guía paso a paso para importar la pre-anotación en CVAT, corregirla y
re-exportarla, en la PC que tenga CVAT. Es la **etapa 2** del pipeline
(`docs/superpowers/specs/2026-07-11-video-gt-lab-design.md`); las etapas 0, 1, 3 y
4 corren en la máquina con GPU. El protocolo de corrección resume el §5 del spec.

> **Contrato que esta etapa valida por primera vez:** el XML que genera
> `preannotate_video` nunca pasó por un CVAT real. El paso 6 (roundtrip) es la
> prueba de que CVAT lo importa y lo re-exporta sin romper el formato. Hacelo
> ANTES de invertir tiempo corrigiendo.

---

## Puesta en marcha del servicio CVAT (PC Linux, una sola vez)

CVAT self-hosted corre con **Docker Compose** usando imágenes prebuildeadas
(no compila nada). Requisitos: Linux x86_64, ~4 GB de RAM libre y ~10 GB de
disco (las imágenes ocupan varios GB y los datos crecen con cada video que
subas). **No hace falta GPU** en esta PC: la inferencia ya se hizo en la
máquina con GPU; acá solo se corrige.

### a) Instalar Docker Engine + Compose plugin (Ubuntu/Debian)

```bash
# Repo oficial de Docker (recomendado; el docker.io de apt suele estar viejo)
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Usar docker sin sudo (cerrar sesión y volver a entrar para que aplique)
sudo usermod -aG docker $USER
```

Verificá: `docker --version` y `docker compose version` responden.

### b) Clonar CVAT y levantar el servicio

```bash
git clone https://github.com/cvat-ai/cvat
cd cvat
# Usar la última release estable, NO la rama develop (default del repo):
git checkout $(git describe --tags --abbrev=0)

# Solo si vas a entrar desde OTRA máquina de la red (si trabajás en esta
# misma PC, omitilo — default localhost):
# export CVAT_HOST=<ip-de-esta-pc>

docker compose up -d          # descarga las imágenes la primera vez (tarda)
docker compose ps             # esperar a que todos estén running/healthy
```

**No hace falta** ningún compose extra (serverless/nuclio, analytics): el
`docker-compose.yml` base alcanza para anotar — el auto-etiquetado ya lo hace
nuestro pipeline afuera.

### c) Crear el usuario admin y entrar

```bash
docker exec -it cvat_server bash -ic 'python3 ~/manage.py createsuperuser'
```

Abrí **http://localhost:8080** en el navegador (o `http://<ip>:8080` desde
otra máquina si exportaste `CVAT_HOST`) y logueate con ese usuario. Listo:
seguí con el paso 0 de abajo.

### d) Operación diaria

| Acción | Comando (desde el dir `cvat/`) |
|---|---|
| Arrancar | `docker compose up -d` |
| Apagar (los datos QUEDAN, viven en volúmenes docker) | `docker compose down` |
| Ver estado / logs | `docker compose ps` / `docker compose logs -f cvat_server` |
| Actualizar CVAT | `git fetch --tags && git checkout <tag-nuevo> && docker compose pull && docker compose up -d` |
| Uso de disco de docker | `docker system df` |

> **Cuidado:** `docker compose down -v` **borra los volúmenes** = todas las
> tasks, anotaciones y usuarios. No lo uses salvo que quieras resetear CVAT
> de cero. Exportá siempre el XML corregido (paso 5) apenas termines un clip:
> el export en `datasets-videos/corrected/` es la copia que importa, no lo
> que vive dentro de CVAT.

---

## 0. Qué llevar a la PC con CVAT

Copiá desde la máquina con GPU estos dos archivos (por clip):

- `datasets-videos/clips/<clip_id>.mp4` — el clip **preparado** (CFR). **Nunca uses
  el video fuente de `raw/`**: la tarea de CVAT tiene que ser exactamente el clip
  que se pre-anotó, si no el mapeo frame↔ms no cierra (la derivación lo detecta y
  falla, ver paso 7).
- `datasets-videos/preann/<clip_id>.xml` — la pre-anotación.

Para el clip de prueba: `lab_recorte1.mp4` + `lab_recorte1.xml`.

También necesitás el JSON de labels (está en el repo, no cambia entre clips):
`datasets/scripts/videogt/cvat_labels.json`.

---

## 1. Crear el proyecto con los labels correctos

En CVAT: **Projects → +** (o directamente una Task). En la sección **Labels**,
elegí **Raw** y pegá el contenido de `cvat_labels.json`:

```json
[
  {
    "name": "person",
    "type": "rectangle",
    "attributes": [
      {"name": "has_helmet", "mutable": true, "input_type": "radio",
       "default_value": "unknown", "values": ["unknown", "true", "false"]},
      {"name": "has_vest", "mutable": true, "input_type": "radio",
       "default_value": "unknown", "values": ["unknown", "true", "false"]}
    ]
  }
]
```

**Por qué importa cada detalle:**
- El label se llama **`person`** en minúscula. La derivación busca ese label
  exacto; si queda `Person` o `Persona`, el script **falla** (guarda anti-error).
- Los atributos son **`radio`** con `unknown / true / false`, default **`unknown`**
  — NO checkbox. Esto es la protección central: un track que dejás en `unknown`
  se lee como "no evaluable" y **no fabrica una infracción**. Si fueran checkbox
  con default `false`, cada persona que no tocás quedaría marcada como "sin casco".
- Son **mutables**: su valor puede cambiar por keyframe a lo largo del track (es lo
  que permite marcar "se saca el casco en el segundo 8").

---

## 2. Crear la Task con el clip preparado

Dentro del proyecto: **+ → Create a new task**.

- **Name:** el `clip_id` (p. ej. `lab_recorte1`).
- **Select files:** subí `<clip_id>.mp4` (el de `clips/`, CFR).
- Dejá el resto por default. **No** actives "Use zip/image chunks" ni recorte:
  el clip ya viene preparado.

Abrí la task cuando termine de procesar el video.

---

## 3. Importar la pre-anotación

En la task (o en el job): menú **Actions → Upload annotations**.

- **Format:** **`CVAT for video 1.1`** (exactamente ese; no "CVAT for images",
  no COCO, no Datumaro).
- Subí `<clip_id>.xml`.
- Confirmá. Deberías ver los tracks de persona con sus cajas y, en el panel de
  objetos, los atributos `has_helmet`/`has_vest` por track.

Si CVAT rechaza el archivo o no aparece ningún track, **pará acá** y avisá: es el
contrato writer→CVAT que estamos validando por primera vez (ver paso 6).

---

## 4. Protocolo de corrección

> El clip de prueba `lab_recorte1` es obra real con ~10 operarios y salió con **41
> tracks** (mucha fragmentación por la maquinaria que cruza). En un clip así el
> grueso del trabajo es **unir tracks fragmentados**, no ajustar cajas.

Orden recomendado (una pasada por cada cosa, no todo a la vez):

1. **Mirá el clip entero una vez** sin tocar nada, para tener contexto.

2. **Tracks (cajas de persona):**
   - **Borrá** falsos positivos (cajas sobre algo que no es una persona).
   - **Uní** (merge) los ids que son la misma persona partida en varios tracks.
   - **Separá** (split) un track que saltó de una persona a otra.
   - Ajustá las cajas gruesas lo justo — no busques perfección pixel a pixel.
   - Marcá **`outside`** SOLO cuando la persona **sale de cuadro de verdad** (eso
     cierra su episodio). Una oclusión parcial (la tapa una máquina) es
     **`occluded`**, la caja sigue viva.

3. **Atributos (`has_helmet` / `has_vest`), lo más importante para el GT:**
   - Recorré **cada transición** que sugirió la pre-anotación y verificala contra
     el video (¿realmente se saca el casco en ese instante?).
   - Buscá transiciones **faltantes** en los tramos largos sin cambios: el
     suavizado del detector pudo comerse un evento corto (esos transitorios
     importan como eventos sub-umbral).
   - Poné **`true`** o **`false`** donde estás seguro. Dejá **`unknown`** SOLO si
     genuinamente no se puede saber (persona muy lejos/ocluida): `unknown` no
     cuenta ni a favor ni en contra, no inventa una infracción.
   - Recordá que el atributo es escalón: fijás el valor en el keyframe donde
     cambia y se mantiene hasta el próximo cambio.

---

## 5. Exportar el XML corregido

Menú **Actions → Export task dataset** (o **Export annotations**).

- **Format:** **`CVAT for video 1.1`** (el mismo de la importación).
- CVAT te da un **.zip**. Descomprimilo: adentro hay un `annotations.xml`.
- Renombralo/guardalo como `<clip_id>.xml` y llevalo de vuelta a la máquina con
  GPU, a `datasets-videos/corrected/<clip_id>.xml`.

---

## 6. Verificar el roundtrip (SOLO la primera vez, en el clip de prueba)

Este paso prueba que CVAT no rompe el formato. En la máquina con GPU:

1. Importá el XML de pre-anotación en CVAT (paso 3) y **exportalo sin editar nada**
   (paso 5) → guardalo como `datasets-videos/corrected/lab_recorte1.roundtrip.xml`.
2. Derivá desde el XML original y desde el exportado, y compará:

```bash
cd e-ovrt_datasets
# desde la pre-anotación original
python3 datasets/scripts/videogt/derive_clip_gt.py \
    --xml datasets-videos/preann/lab_recorte1.xml \
    --clip-yaml datasets-videos/lab_recorte1.clip.yaml \
    --info datasets-videos/clips/lab_recorte1.info.json \
    --out /tmp/gt_from_preann.json
# desde el export de CVAT sin editar
python3 datasets/scripts/videogt/derive_clip_gt.py \
    --xml datasets-videos/corrected/lab_recorte1.roundtrip.xml \
    --clip-yaml datasets-videos/lab_recorte1.clip.yaml \
    --info datasets-videos/clips/lab_recorte1.info.json \
    --out /tmp/gt_from_cvat.json
# deben ser equivalentes en episodios/sub-umbral (puede diferir 'provenance.xml_sha256')
diff <(jq 'del(.provenance)' /tmp/gt_from_preann.json) \
     <(jq 'del(.provenance)' /tmp/gt_from_cvat.json) && echo "ROUNDTRIP OK"
```

Si `ROUNDTRIP OK`, el contrato writer→CVAT→parser está validado y ya podés confiar
en la herramienta. Si el `diff` muestra diferencias, guardá ambos JSON y el
`.roundtrip.xml` y avisá — significa que CVAT reinterpreta algo del formato y hay
que ajustar el writer o el parser.

---

## 7. Derivar el GT final y validarlo

Con el XML **corregido** (el de verdad, no el roundtrip):

```bash
cd e-ovrt_datasets
python3 datasets/scripts/videogt/derive_clip_gt.py \
    --xml datasets-videos/corrected/lab_recorte1.xml \
    --clip-yaml datasets-videos/lab_recorte1.clip.yaml \
    --info datasets-videos/clips/lab_recorte1.info.json \
    --out datasets-videos/gt/lab_recorte1.json
    # para el banco real: agregá --pattern-set "CR-01=<ms>,CR-02=<ms>" según la corrida
```

El `<clip_id>.clip.yaml` debe traer `clip_id`, `block`, `scenario` y `level`
(`scene` o `subject`, exacto — un typo hace fallar la derivación con error
claro, no cae en silencio a scene). Campos opcionales: `source_id` (default =
`clip_id`; es la identidad que el evaluador matchea contra las alertas),
`recording`, `annotation`. Ejemplo completo: `lab_recorte1.clip.yaml`.

El script imprime un **timeline legible** (episodios + sub-umbral por sujeto).
**Revisalo contra el video** — es la última verificación humana (la "regla de oro":
el GT sale del video, el script solo hace la aritmética).

Después validá:

```bash
python3 datasets/scripts/bench/validate_clip_gt.py --gt-dir datasets-videos/gt
```

Debe decir `✓ validate_clip_gt: 0 error(es)`. Errores comunes y qué significan:
- *"no hay tracks 'person'"* → el export salió vacío o el label quedó mal escrito
  (volvé al paso 1/3). Si el clip es un negativo intencional, usá `--allow-empty`.
- *"el `<size>` del XML difiere de n_frames"* → la task de CVAT no se creó con el
  clip preparado (paso 2). Rehacé la task con el `.mp4` de `clips/`.

---

## 8. Doble anotación (para ≥20% de los clips del banco)

Un segundo anotador corrige **la misma pre-anotación** de forma independiente,
exporta su XML, y se deriva por separado. Después:

```bash
python3 datasets/scripts/videogt/compare_annotations.py \
    --a datasets-videos/gt/<clip_id>.json \
    --b datasets-videos/gt/<clip_id>.anotador2.json
```

Emite el **kappa de Cohen** por condición + |Δstart|/|Δend| medianos, que van al
reporte de calidad del GT (spec 43 §4.2).

---

## Referencia rápida de formatos

| Momento | Formato en CVAT |
|---|---|
| Importar pre-anotación | `CVAT for video 1.1` (Upload annotations) |
| Exportar corrección | `CVAT for video 1.1` (Export task dataset → .zip → annotations.xml) |
| Label | `person` (rectangle) |
| Atributos | `has_helmet`, `has_vest` — radio `unknown/true/false`, default `unknown` |

Notas de UI: la redacción de los menús cambia levemente entre versiones de CVAT
(self-hosted vs cvat.ai). "Upload/Export annotations" puede aparecer como acción de
la task o del job; el **formato** (`CVAT for video 1.1`) es lo que no puede variar.

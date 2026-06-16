# Estrategia de videos stock para evaluacion del pipeline

Fecha: 2026-06-16

## Contexto

El esquema actual de datasets curados se mantiene orientado a fine-tuning de
detectores sobre las clases canonicas del proyecto. Esa linea no se modifica.

La nueva necesidad es diferente: evaluar el pipeline completo sobre clips de
video donde una observacion pueda persistir durante una ventana temporal. Esto
permite validar el comportamiento integrado del plano de medios y el plano de
control, especialmente:

- persistencia temporal de condiciones observadas;
- descarte de detecciones transitorias;
- generacion de alertas luego de una ventana de confirmacion;
- falsos positivos por minuto;
- falsos negativos ante condiciones persistentes;
- tiempo hasta alerta.

## Decision Principal

Para evaluacion temporal no conviene comenzar con anotacion exhaustiva de
bounding boxes frame a frame. Ese costo esta mas justificado para entrenamiento o
evaluacion fina del detector.

La estrategia adoptada para esta etapa es usar anotacion temporal debil:

- nivel clip o intervalo;
- condicion esperada;
- visibilidad del trabajador;
- estado esperado de casco/chaleco cuando sea evidente;
- notas de incertidumbre o descarte.

Ejemplo:

```csv
clip_id,source,condition,start_s,end_s,worker_visible,helmet_state,vest_state,usable,notes
pixabay_42923_000,pixabay,CR-01,1.0,6.0,true,not_worn,unknown,true,"worker visible in construction scene"
```

## Fuentes

Se priorizan fuentes con API oficial para evitar scraping y mejorar
reproducibilidad:

- Pexels API: busqueda de videos, metadata, autor, previews y variantes MP4.
- Pixabay API: busqueda de videos, metadata y variantes MP4.

Otras plataformas como Mixkit o Videezy pueden revisarse manualmente, pero no se
recomienda automatizarlas sin API oficial y terminos claros.

## Flujo Propuesto

1. Buscar candidatos por API usando queries controladas.
2. Guardar metadata y trazabilidad legal.
3. Descargar solo versiones livianas o previews.
4. Generar contact sheets con frames representativos.
5. Revisar humanamente las hojas de contacto.
6. Marcar candidatos como `keep`, `discard` o `uncertain`.
7. Descargar/normalizar solo los candidatos aprobados.
8. Cortar clips de 4 a 8 segundos cuando corresponda.
9. Ejecutar el pipeline completo sobre esos clips.
10. Comparar alertas generadas contra ground truth temporal debil.

## Metadata Minima

Por cada candidato se debe conservar:

- fuente;
- id de fuente;
- URL publica;
- autor;
- URL del autor si existe;
- licencia;
- URL de licencia;
- query que produjo el resultado;
- duracion;
- resolucion;
- FPS si esta disponible;
- path local de video liviano;
- path local de contact sheet;
- decision de revision.

## Queries Iniciales

Queries probadas o recomendadas:

- `construction worker`
- `hard hat worker`
- `safety vest construction`
- `construction site people`
- `construction safety vest`
- `construction hard hat`
- `road worker safety vest`
- `industrial worker helmet`

Las queries mas especificas redujeron casos desalineados respecto del objetivo.

## Resultado De La PoC

Se implemento `datasets/scripts/video_stock/video_stock_poc.py`.

Primera corrida:

- Fuentes: Pexels y Pixabay.
- Pexels respondio `HTTP 403`.
- Pixabay funciono.
- Se generaron 5 candidatos.
- Un caso resulto desalineado con lo esperado: `005_pixabay_1635.mp4`.

Segunda corrida:

- Fuente: Pixabay.
- Queries mas especificas.
- Se generaron 8 candidatos.
- La alineacion preliminar fue mejor.

Las salidas locales generadas fueron eliminadas para no ocupar espacio y no se
versionan. El patron `datasets/interim/video_stock_poc*/` fue agregado a
`.gitignore`.

## Uso De La PoC

Ver:

```text
datasets/scripts/video_stock/README.md
```

## Recomendacion Operativa

La proxima iteracion deberia mantener la misma filosofia:

- pocas queries;
- pocos candidatos;
- revision por contact sheets;
- descarte agresivo;
- ninguna descarga masiva;
- solo pasar a normalizacion los clips marcados como `keep`.

Una vez validada la utilidad del flujo, se puede agregar scoring automatico con
el media-plane o con un detector auxiliar para ordenar candidatos por probabilidad
de contener trabajadores y EPP visible.

## Conclusion

La estrategia viable para evaluacion del pipeline es:

API oficial + metadata trazable + descarga liviana + contact sheets + revision
humana minima + ground truth temporal debil.

Esto minimiza el trabajo humano sin confundir esta linea con el dataset de
fine-tuning existente.


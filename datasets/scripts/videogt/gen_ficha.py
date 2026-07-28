"""Genera la ficha de eventos (doc 72 §5.5) desde los artefactos del recorte.

IMPORTANTE: las marcas se DERIVAN del episode_draft (o sea, de los clicks del
operador en la consola), no son una medicion independiente del video. Eso queda
declarado en el encabezado de la ficha.
"""
import json, pickle, pathlib, subprocess

SC = pathlib.Path('/tmp/claude-1000/-home-simonll4-projects/7b6da9f0-d6f5-4fab-9e61-009a703137b8/scratchpad')
DV = pathlib.Path('/home/simonll4/projects/e-ovrt_datasets/datasets-videos')
rows = sorted(pickle.load(open(SC / 'final.pkl', 'rb')), key=lambda r: (r['sc'], r['cid']))

PRE_ROLL = 3.5
# etiquetas de marca por escenario (doc 72 §5.5), alineadas con MARK_LABELS de la consola
MARCAS = {
    'P1': ['casco_fuera', 'casco_puesto'],
    'P2': ['chaleco_fuera', 'chaleco_puesto'],
    'P3': ['casco_fuera', 'casco_puesto'],
    'P4': ['casco_fuera', 'casco_puesto'],
    'P5': ['ambos_en_cuadro', 'fin_tramo_limpio'],
    'P6': ['casco_fuera', 'chaleco_fuera', 'chaleco_puesto', 'casco_puesto'],
    'P7': ['casco_fuera', 'casco_puesto'],
    'P8': ['casco_fuera', 'sale_de_cuadro', 'vuelve', 'casco_puesto'],
    'P9': ['sujeto_completo_en_cuadro', 'fin_accion'],
}
NOTA = {
    'casco_fuera': 'onset ep. casco', 'casco_puesto': 'fin ep. casco',
    'chaleco_fuera': 'onset ep. chaleco', 'chaleco_puesto': 'fin ep. chaleco',
    'ambos_en_cuadro': 'inicio tramo limpio (sin episodio)',
    'fin_tramo_limpio': 'fin tramo limpio (sin episodio)',
    'sale_de_cuadro': 'fin ep. 1 (sale de cuadro)', 'vuelve': 'onset ep. 2 (reingresa sin casco)',
    'sujeto_completo_en_cuadro': 'onset ep. (entra ya en infraccion)',
    'fin_accion': 'fin ep. (sale de cuadro / termina)',
}


def sidecar(master_name):
    p = DV / 'raw' / master_name.replace('.mp4', '.rec.json')
    if not p.is_file():
        return {}
    return json.loads(p.read_text())


def cam(sc):
    plugin = sc.get('plugin', '')
    # doc 71 §1: la camara sale del sidecar, no del nombre. rtsp = DVR comodity.
    return {'oak_d': 'OAK-D', 'rtsp': 'DVR'}.get(plugin, plugin or '?')


# Marcas MEDIDAS visualmente sobre el video (tira de miniaturas, §5.4), en
# coordenadas del master. Estas tienen prioridad sobre las derivadas del borrador.
VERIFICADO = {
    'a_p3_c01': {'casco_fuera': 5.10, 'casco_puesto': 7.90},
    'a_p3_c02': {'casco_fuera': 5.80, 'casco_puesto': 8.10},
}


def marcas_de(r):
    """Reconstruye las marcas en coordenadas del MASTER desde el episode_draft + ss."""
    ss = r['ss']
    eps = r['eps']
    labels = MARCAS[r['sc']]
    out = []
    if r['sc'] == 'P6':      # anidado: CR-01=[t1,t4]  CR-02=[t2,t3]
        a, b = eps[0], eps[1]
        pares = [(labels[0], a['onset_ms'], 'CR-01'), (labels[1], b['onset_ms'], 'CR-02'),
                 (labels[2], b['end_ms'], 'CR-02'), (labels[3], a['end_ms'], 'CR-01')]
    elif r['sc'] == 'P8':    # secuencial: ep1=[t1,t2]  ep2=[t3,t4]
        a, b = eps[0], eps[1]
        pares = [(labels[0], a['onset_ms'], 'CR-01'), (labels[1], a['end_ms'], 'CR-01'),
                 (labels[2], b['onset_ms'], 'CR-01'), (labels[3], b['end_ms'], 'CR-01')]
    else:
        e = eps[0]
        cond = e.get('condition') or '—'
        pares = [(labels[0], e['onset_ms'], cond), (labels[1], e['end_ms'], cond)]
    ver = VERIFICADO.get(r['cid'], {})
    for lbl, ms, cond in pares:
        if lbl in ver:
            out.append((lbl, ver[lbl], cond, True))      # medido sobre el video
        else:
            out.append((lbl, ss + ms / 1000.0, cond, False))
    return out


L = []
L.append('# Ficha de eventos — rodaje 2026-07-25 (Bloque A)')
L.append('')
L.append('**Generada:** 2026-07-27, desde los artefactos del recorte.')
L.append('')
L.append('> ⚠️ **Procedencia de las marcas, leer antes de usar.** Los tiempos de este')
L.append('> documento están **derivados del `episode_draft`** que escribió la consola —')
L.append('> es decir, de las marcas que hizo el operador al recortar — y del `ss`')
L.append('> recuperado por matching de frames contra el master. **No son una medición')
L.append('> independiente del video.** Sirven como expectativa escrita para el chequeo')
L.append('> cruzado contra CVAT (detectan clip equivocado, atributo invertido y `unknown`')
L.append('> que parte un episodio), pero **no detectan un error sistemático de marcado**.')
L.append('> Las filas verificadas contra el video están marcadas con ✅ en la columna `v`')
L.append('> (medidas con tira de miniaturas, §5.4); el resto lleva ⋯ y sigue pendiente.')
L.append('')
L.append('> **La ficha no es el ground truth.** El GT sale de CVAT frame a frame vía')
L.append('> `derive_clip_gt.py`. Discrepancia ficha↔GT por debajo de 0,5 s: normal, se')
L.append('> ignora. Por encima de 1,0 s: se investiga antes de promover el clip.')
L.append('')
L.append('---')
L.append('')
L.append('## Índice')
L.append('')
L.append('| clip_id | master | cám | esc | dur master | ss | D | frames | estado |')
L.append('|---|---|---|---|---:|---:|---:|---:|---|')
for r in rows:
    m = r['master'].replace('raw/', '')
    sc = sidecar(m)
    dm = sc.get('measured', {}).get('duration_ms')
    dm = f'{dm/1000:.1f} s' if dm else '?'
    L.append(f"| `{r['cid']}` | `{m}` | {cam(sc)} | {r['sc']} | {dm} | "
             f"{r['ss']:.2f} | {r['dur']/1000:.2f} | {r['fr']} | recortado |")
L.append('')
L.append(f'**Total:** {len(rows)} clips · {sum(r["fr"] for r in rows)} frames a anotar '
         f'(~{sum(r["fr"] for r in rows)/30/60:.1f} min de video).')
L.append('')
L.append('---')
L.append('')
L.append('## Bloques por clip')
L.append('')

for r in rows:
    m = r['master'].replace('raw/', '')
    sc = sidecar(m)
    dm = sc.get('measured', {}).get('duration_ms')
    dm = f'{dm/1000:.1f} s' if dm else '?'
    L.append(f"### {r['cid']} — master `{m}` ({cam(sc)}, {dm}) — escenario {r['sc']}")
    L.append('')
    L.append('| # | marca | t (s) | condición | v | nota |')
    L.append('|---|---|---:|---|:-:|---|')
    marcas = marcas_de(r)
    for i, (lbl, t, cond, verif) in enumerate(marcas, 1):
        nota = NOTA.get(lbl, '')
        if r['sc'] == 'P3' and lbl == 'casco_puesto':
            nota = 'fin REAL del transitorio (la marca del recorte fue artificial, ver abajo)'
        L.append(f"| {i} | `{lbl}` | {t:.2f} | {cond} | {'✅' if verif else '⋯'} | {nota} |")
    L.append('')
    eps_reales = [e for e in r['eps'] if e.get('condition')]
    if eps_reales:
        esp = ' · '.join(f"{e['condition']} [{e['onset_ms']}, {e['end_ms']}]" for e in eps_reales)
        L.append(f"**Episodios esperados en el GT:** {esp} (ms, ±500)")
    elif r['sc'] == 'P3':
        ss = r['ss']
        t1 = next(t for lbl, t, _, _ in marcas if lbl == 'casco_fuera')
        t2 = next(t for lbl, t, _, _ in marcas if lbl == 'casco_puesto')
        a, b, dur = round((t1 - ss) * 1000), round((t2 - ss) * 1000), round((t2 - t1) * 1000)
        L.append(f"**Episodios esperados en el GT:** ninguno — `sub_threshold_event` "
                 f"[{a}, {b}] ms, transitorio de **{dur} ms** (< 4000 ms, por eso NO es episodio).")
        L.append('')
        L.append(f"> ⚠️ **La marca `casco_puesto` del recorte fue artificial** "
                 f"(t1 + 12 s = {ss + r['eps'][0]['end_ms']/1000:.2f} s) para estirar el clip a la "
                 f"duración que pide el guion. El transitorio REAL termina a los **{t2:.2f} s** del "
                 f"master, que es lo que va a mostrar CVAT. El `episode_draft` del `.clip.yaml` NO "
                 f"refleja esto — usar esta ficha, no el borrador, para el chequeo cruzado.")
    else:
        L.append("**Episodios esperados en el GT:** ninguno — `negative: true` (cumplimiento total)")
    L.append('')
    L.append(f"Recorte: ss = **{r['ss']:.2f}** · D = **{r['dur']/1000:.2f} s** · onset_rel = "
             f"**{(eps_reales[0]['onset_ms'] if eps_reales else r['eps'][0]['onset_ms'])} ms**")
    if r['warns']:
        L.append('')
        for w in r['warns']:
            L.append(f"> ⚠️ {w}")
    L.append('')
    L.append('Cuadro limpio: ⋯ · Notas de anotación: ⋯')
    L.append('')

out = SC / 'ficha-eventos-rodaje.md'
out.write_text('\n'.join(L), encoding='utf-8')
print(f'escrita: {out}  ({len(L)} lineas)')

"""Evaluación: (A) las 12 predicciones reales del chat, (B) modelo v2 reconstruido en los 104 partidos,
(C) Monte Carlo 10,000. Rivales: solo ranking FIFA y solo Elo."""
import csv, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import modelo
from modelo import ROOT, cargar_equipos, cargar_sedes, puntaje, beta_desde_puntajes, prob_1x2, prob_avanza
from simulacion import simular, FASES

OUT = os.path.join(ROOT, 'resultados'); os.makedirs(OUT, exist_ok=True)
E = cargar_equipos(); S = cargar_sedes()
M = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'processed', 'mundial2026_partidos.csv'), encoding='utf-8')))

_EL = [e['elo_pre'] for e in E.values()]; _LO, _HI = min(_EL), max(_EL)
def puntaje_forma_nivel(e, s):
    """ANÁLISIS DE SENSIBILIDAD POST HOC (definido después de ver los resultados):
    igual que el v2 reconstruido, pero Forma = nivel de Elo reescalado a 1–10 en lugar del cambio en 12 meses."""
    x = dict(e); x['v_forma'] = 1 + 9 * (e['elo_pre'] - _LO) / (_HI - _LO); return puntaje(x, s)

PRINCIPAL = 'v2 reconstruido'
POSTHOC = 'v2 · forma = nivel Elo (post hoc)'
MODELOS = {
    'v2 reconstruido': lambda e, s: puntaje(e, s),
    POSTHOC: puntaje_forma_nivel,
    'Solo ranking FIFA': lambda e, s: e['v_fifa'],
    'Solo Elo': lambda e, s: e['elo_pre'] / 100,
}
def betas(ratio=None):
    if ratio: modelo.RATIO_95 = ratio
    b = {k: beta_desde_puntajes([f(e, None) for e in E.values()])[0] for k, f in MODELOS.items()}
    modelo.RATIO_95 = 6.0
    return b

def brier(p, o):   # p=(L,E,V), o índice real
    return sum((p[i] - (1 if i == o else 0)) ** 2 for i in range(3))

def evaluar_104(ratio=6.0):
    B = betas(ratio); filas = []
    for m in M:
        o = {'L': 0, 'E': 1, 'V': 2}[m['resultado_90']]; s = S[m['sede']]
        fila = dict(match_id=int(m['match_id']), fase=m['fase'], local=m['local'], visitante=m['visitante'], real=m['resultado_90'])
        for k, f in MODELOS.items():
            d = f(E[m['local']], s) - f(E[m['visitante']], s)
            p = prob_1x2(d, B[k] if ratio == 6.0 else betas(ratio)[k])
            fila[k] = dict(p=[round(x, 4) for x in p], brier=brier(p, o), logloss=-math.log(p[o]), acierto=int(np.argmax(p) == o))
        p = (1/3, 1/3, 1/3); fila['Uniforme (1/3)'] = dict(p=list(p), brier=brier(p, o), logloss=-math.log(1/3), acierto=0)
        filas.append(fila)
    return filas, B

def resumen(filas, claves):
    out = {}
    for k in claves:
        b = np.array([f[k]['brier'] for f in filas]); l = np.array([f[k]['logloss'] for f in filas]); a = np.array([f[k]['acierto'] for f in filas])
        out[k] = dict(brier=b.mean(), logloss=l.mean(), aciertos=int(a.sum()), n=len(filas))
    return out

def bootstrap_dif(filas, k1, k2, n=10000, seed=1):
    rng = np.random.default_rng(seed); d = np.array([f[k1]['brier'] - f[k2]['brier'] for f in filas])
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n)]
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)

# ---------- (A) las 12 predicciones reales ----------
PRED = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'raw', 'predicciones_registradas_chat.csv'), encoding='utf-8')))
TABLA_CHAT = [8.8,8.5,8.9,8.1,8.2,7.3,7.8,7.7,7.3,7.3,7.1,7.2,7.7,7.8,7.8,6.7,6.9,6.3,6.2,6.2]   # totales reportados, tabla del 25-jun
def evaluar_12():
    beta_chat, d95 = beta_desde_puntajes(TABLA_CHAT)
    filas = []
    for m in M:
        if not m['pred_version']: continue
        o = {'L': 0, 'E': 1, 'V': 2}[m['resultado_90']]
        f = dict(match_id=int(m['match_id']), fase=m['fase'], partido=f"{m['local']}–{m['visitante']}", version=m['pred_version'],
                 pred=m['pred_emitida'], pred_v0=m['pred_v0'], real_90=f"{m['goles_local_90']}-{m['goles_visitante_90']}",
                 avanza=m['avanza'], acierto=m['acierto_emitida'])
        if m['puntaje_local_reportado']:
            d = float(m['puntaje_local_reportado']) - float(m['puntaje_visitante_reportado'])
            p = prob_1x2(d, beta_chat); f['p_chat'] = [round(x, 3) for x in p]; f['brier_chat'] = brier(p, o)
        s = S[m['sede']]
        p2 = prob_1x2(puntaje(E[m['local']], s) - puntaje(E[m['visitante']], s), betas()['v2 reconstruido'])
        pf = prob_1x2(E[m['local']]['v_fifa'] - E[m['visitante']]['v_fifa'], betas()['Solo ranking FIFA'])
        f['brier_v2r'] = brier(p2, o); f['brier_fifa'] = brier(pf, o)
        filas.append(f)
    return filas, beta_chat

def etapa_real():
    llego = {e: 0 for e in E}
    orden = {'Dieciseisavos': 1, 'Octavos': 2, 'Cuartos': 3, 'Semifinal': 4, 'Final': 5}
    for m in M:
        if m['fase'] in orden:
            for t in (m['local'], m['visitante']): llego[t] = max(llego[t], orden[m['fase']])
            if m['fase'] == 'Final': llego[m['avanza']] = 6
    return llego

if __name__ == '__main__':
    filas, B = evaluar_104()
    claves = list(MODELOS) + ['Uniforme (1/3)']
    R = dict(betas=B, resumen_104=resumen(filas, claves))
    R['por_fase'] = {fase: resumen([f for f in filas if (f['fase'] == 'Grupos') == (fase == 'Grupos')], claves) for fase in ['Grupos', 'Eliminatorias']}
    R['bootstrap'] = {k: bootstrap_dif(filas, 'v2 reconstruido', k) for k in ['Solo ranking FIFA', 'Solo Elo', 'Uniforme (1/3)']}
    R['bootstrap_posthoc'] = {k: bootstrap_dif(filas, POSTHOC, k) for k in ['Solo Elo', 'Solo ranking FIFA', 'v2 reconstruido']}
    # Brier de las 12 reales según el supuesto de conversión (depende de la regla, no solo del modelo)
    sens12 = {}
    for r in (3.0, 4.0, 6.0, 9.0):
        modelo.RATIO_95 = r; b, _ = beta_desde_puntajes(TABLA_CHAT); modelo.RATIO_95 = 6.0
        xs = [m for m in M if m['puntaje_local_reportado']]
        sens12[str(r)] = float(np.mean([brier(prob_1x2(float(m['puntaje_local_reportado']) - float(m['puntaje_visitante_reportado']), b),
                                              {'L': 0, 'E': 1, 'V': 2}[m['resultado_90']]) for m in xs]))
    R['sensibilidad_12'] = sens12
    R['sensibilidad'] = {str(r): {k: v['brier'] for k, v in resumen(evaluar_104(r)[0], claves).items()} for r in (4.0, 6.0, 9.0)}
    f12, bchat = evaluar_12(); R['doce'] = f12; R['beta_chat'] = bchat
    real = etapa_real(); R['etapa_real'] = real
    sims = {}
    for k, f in MODELOS.items():
        sim = simular(n=10000, fuerza=f, beta=B[k])
        sims[k] = {e: v.tolist() for e, v in sim.items()}
        # verosimilitud de la fase real alcanzada: P(llegar a fase r) − P(llegar a r+1)
        ll = []
        for e, v in sim.items():
            r = real[e]; p = v[r] - (v[r + 1] if r + 1 < len(v) else 0)
            ll.append(math.log(max(p, 1e-4)))
        R.setdefault('mc_loglik', {})[k] = float(np.mean(ll))
    R['montecarlo'] = sims
    json.dump(R, open(os.path.join(OUT, 'resultados.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    with open(os.path.join(OUT, 'probabilidades_104.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['match_id', 'fase', 'local', 'visitante', 'real_90'] + [f'{k} {x}' for k in MODELOS for x in ('pL', 'pE', 'pV')])
        for f in filas: w.writerow([f['match_id'], f['fase'], f['local'], f['visitante'], f['real']] + [x for k in MODELOS for x in f[k]['p']])
    with open(os.path.join(OUT, 'puntajes_48_equipos.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['equipo', 'grupo', 'FIFA', 'Top5', 'Edad', 'Continuidad', 'Forma', 'puntaje_sin_clima(clima=7)', 'elo_pre', 'delta_elo_12m'])
        for e in sorted(E, key=lambda e: -puntaje(E[e])):
            r = E[e]; w.writerow([e, r['grupo']] + [round(r[k], 2) for k in ('v_fifa', 'v_top5', 'v_edad', 'v_cont', 'v_forma')] + [round(puntaje(r), 2), round(r['elo_pre']), round(r['elo_delta_12m'])])
    print(json.dumps({k: R[k] for k in ('betas', 'resumen_104', 'por_fase', 'bootstrap', 'bootstrap_posthoc', 'sensibilidad', 'sensibilidad_12', 'mc_loglik', 'beta_chat')}, ensure_ascii=False, indent=1, default=float))

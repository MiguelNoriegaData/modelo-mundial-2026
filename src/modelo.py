"""Modelo v2 reconstruido con datos públicos previos al 11 de junio de 2026.
Fórmula congelada (pesos de la v2 del chat original):
    puntaje = 0.20·FIFA + 0.20·Top5 + 0.10·Edad + 0.10·Continuidad + 0.30·Forma + 0.10·Clima
Todas las variables en escala 1–10 con reglas fijas (ver REGLAS)."""
import csv, math, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from elo import elo_history, rating_at

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
CORTE = '2026-06-11'          # nada posterior a esta fecha entra al modelo
PESOS = dict(fifa=.20, top5=.20, edad=.10, cont=.10, forma=.30, clima=.10)

EN = {'México':'Mexico','Sudáfrica':'South Africa','Corea del Sur':'South Korea','Chequia':'Czech Republic','Canadá':'Canada','Bosnia y Herzegovina':'Bosnia and Herzegovina','EE.UU.':'United States','Paraguay':'Paraguay','Catar':'Qatar','Suiza':'Switzerland','Brasil':'Brazil','Marruecos':'Morocco','Haití':'Haiti','Escocia':'Scotland','Australia':'Australia','Turquía':'Turkey','Alemania':'Germany','Curazao':'Curaçao','Países Bajos':'Netherlands','Japón':'Japan','Costa de Marfil':'Ivory Coast','Ecuador':'Ecuador','Suecia':'Sweden','Túnez':'Tunisia','España':'Spain','Cabo Verde':'Cape Verde','Bélgica':'Belgium','Egipto':'Egypt','Arabia Saudita':'Saudi Arabia','Uruguay':'Uruguay','Irán':'Iran','Nueva Zelanda':'New Zealand','Francia':'France','Senegal':'Senegal','Irak':'Iraq','Noruega':'Norway','Argentina':'Argentina','Argelia':'Algeria','Austria':'Austria','Jordania':'Jordan','Portugal':'Portugal','RD Congo':'DR Congo','Inglaterra':'England','Croacia':'Croatia','Ghana':'Ghana','Panamá':'Panama','Uzbekistán':'Uzbekistan','Colombia':'Colombia'}

REGLAS = {
 'fifa':  'FIFA = 10 − 9·(rank−1)/84  (rank 1 → 10, rank 85 → 1)',
 'top5':  'Top5 = 1 + 9·(% de la plantilla en 1a división de ENG/ESP/ITA/GER/FRA 2025-26)',
 'edad':  'Edad = 10 − 3·|edad_promedio − 27|  (pico 25–29; 27 = centro), mínimo 1',
 'cont':  'Continuidad = 1 + 9·min(meses del técnico al 11-jun-2026, 96)/96',
 'forma': 'Forma = cambio de Elo entre 11-jun-2025 y 11-jun-2026, reescalado min–max a 1–10 entre los 48',
 'clima': 'Clima (por partido) = 10 − 0.3·|T_sede − T_casa| − penalización de altitud; estadios climatizados T_sede = 22 °C',
}

def _meses(yyyymm, corte=CORTE):
    y, m = map(int, yyyymm.split('-')); cy, cm = int(corte[:4]), int(corte[5:7])
    return (cy - y) * 12 + (cm - m)

def cargar_equipos():
    E = {r['equipo']: r for r in csv.DictReader(open(os.path.join(RAW, 'equipos_pretorneo.csv'), encoding='utf-8'))}
    for r in csv.DictReader(open(os.path.join(RAW, 'tecnicos_nombramiento.csv'), encoding='utf-8')):
        E[r['equipo']]['meses_tecnico'] = _meses(r['nombrado'])
    for r in csv.DictReader(open(os.path.join(RAW, 'clima_equipos.csv'), encoding='utf-8')):
        E[r['equipo']]['t_casa'] = float(r['temp_media_anual_c']); E[r['equipo']]['alt_casa'] = float(r['altitud_m'])
    _, H = elo_history(os.path.join(RAW, 'results.csv'), CORTE)
    for e, r in E.items():
        r['elo_pre'] = rating_at(H, EN[e], CORTE)
        r['elo_delta_12m'] = r['elo_pre'] - rating_at(H, EN[e], '2025-06-11')
    d = [r['elo_delta_12m'] for r in E.values()]; lo, hi = min(d), max(d)
    for r in E.values():
        r['v_fifa']  = 10 - 9 * (int(r['ranking_fifa_pre']) - 1) / 84
        r['v_top5']  = 1 + 9 * float(r['top5_pct']) / 100
        r['v_edad']  = max(1.0, 10 - 3 * abs(float(r['edad_promedio']) - 27))
        r['v_cont']  = 1 + 9 * min(r['meses_tecnico'], 96) / 96
        r['v_forma'] = 1 + 9 * (r['elo_delta_12m'] - lo) / (hi - lo)
    return E

def cargar_sedes():
    return {r['sede']: dict(t=float(r['temp_media_jun_jul_c']) if r['techo_climatizado'] == 'no' else 22.0,
                            alt=float(r['altitud_m'])) for r in csv.DictReader(open(os.path.join(RAW, 'clima_sedes.csv'), encoding='utf-8'))}

def v_clima(eq, sede):
    pen_alt = 0.0
    if sede['alt'] > 1000:   # solo CDMX (2240 m) y Guadalajara (1566 m)
        pen_alt = 3.0 * (sede['alt'] / 2240) * max(0.0, 1 - eq['alt_casa'] / sede['alt'])
    return max(1.0, min(10.0, 10 - 0.3 * abs(sede['t'] - eq['t_casa']) - pen_alt))

def puntaje(eq, sede=None, pesos=PESOS):
    clima = v_clima(eq, sede) if sede else 7.0
    return (pesos['fifa'] * eq['v_fifa'] + pesos['top5'] * eq['v_top5'] + pesos['edad'] * eq['v_edad'] +
            pesos['cont'] * eq['v_cont'] + pesos['forma'] * eq['v_forma'] + pesos['clima'] * clima)

# ---------- de puntaje a probabilidades (regla fija, sin calibrar con 2026) ----------
GOLES_BASE = 1.30     # promedio histórico ≈ 2.6 goles por partido en Mundiales
RATIO_95 = 6.0        # supuesto a priori: en el desequilibrio "percentil 95" el favorito espera 6 veces más goles

def beta_desde_puntajes(puntajes):
    """β tal que exp(2·β·d95) = RATIO_95, con d95 = percentil 95 de |diferencias| entre todos los pares.
    Solo usa los puntajes previos (nada de resultados)."""
    ds = sorted(abs(a - b) for i, a in enumerate(puntajes) for b in puntajes[i + 1:])
    d95 = ds[int(0.95 * (len(ds) - 1))]
    return math.log(RATIO_95) / (2 * d95), d95

def lambdas(d, beta):
    return GOLES_BASE * math.exp(beta * d), GOLES_BASE * math.exp(-beta * d)

def _pois(l, k): return math.exp(-l) * l ** k / math.factorial(k)

def prob_1x2(d, beta, maxg=12):
    la, lb = lambdas(d, beta)
    pa = [_pois(la, k) for k in range(maxg)]; pb = [_pois(lb, k) for k in range(maxg)]
    w = sum(pa[i] * pb[j] for i in range(maxg) for j in range(maxg) if i > j)
    e = sum(pa[i] * pb[i] for i in range(maxg))
    s = w + e + sum(pa[i] * pb[j] for i in range(maxg) for j in range(maxg) if i < j)
    return w / s, e / s, 1 - (w + e) / s

def prob_avanza(d, beta):
    """Eliminatoria: 90' → tiempo extra (λ/3) → penales 50/50."""
    w, e, l = prob_1x2(d, beta)
    la, lb = lambdas(d, beta)
    w2, e2, l2 = prob_1x2_l(la / 3, lb / 3)
    return w + e * (w2 + e2 * 0.5)

def prob_1x2_l(la, lb, maxg=10):
    pa = [_pois(la, k) for k in range(maxg)]; pb = [_pois(lb, k) for k in range(maxg)]
    w = sum(pa[i] * pb[j] for i in range(maxg) for j in range(maxg) if i > j)
    e = sum(pa[i] * pb[i] for i in range(maxg))
    return w, e, 1 - w - e

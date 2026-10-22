"""Elo de selecciones calculado desde cero con la fórmula de eloratings.net.
Solo se usa para medir la FORMA previa al torneo (cambio de Elo en 12 meses)."""
import csv, math
from collections import defaultdict

def k_factor(t):
    if t == 'FIFA World Cup': return 60
    if t in ('UEFA Euro','Copa América','African Cup of Nations','AFC Asian Cup','Gold Cup','Confederations Cup','CONCACAF Championship','Oceania Nations Cup'): return 50
    if 'qualification' in t or 'Nations League' in t: return 40
    if t == 'Friendly': return 20
    return 30

def gd_mult(n):
    n = abs(n)
    return 1 if n <= 1 else 1.5 if n == 2 else (11 + n) / 8

def elo_history(results_csv, until):
    """Devuelve dict equipo -> lista [(fecha, rating)] usando solo partidos con fecha < until."""
    R = defaultdict(lambda: 1500.0); H = defaultdict(list)
    rows = sorted(csv.DictReader(open(results_csv, encoding='utf-8')), key=lambda r: r['date'])
    for r in rows:
        if r['date'] >= until: break
        if r['home_score'] in ('', 'NA') or r['away_score'] in ('', 'NA'): continue
        a, b = r['home_team'], r['away_team']; ga, gb = int(r['home_score']), int(r['away_score'])
        dr = R[a] - R[b] + (0 if r['neutral'] == 'TRUE' else 100)
        we = 1 / (10 ** (-dr / 400) + 1)
        w = 1 if ga > gb else 0.5 if ga == gb else 0
        d = k_factor(r['tournament']) * gd_mult(ga - gb) * (w - we)
        R[a] += d; R[b] -= d
        H[a].append((r['date'], R[a])); H[b].append((r['date'], R[b]))
    return R, H

def rating_at(H, team, date):
    v = 1500.0
    for d, r in H[team]:
        if d < date: v = r
        else: break
    return v

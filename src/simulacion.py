"""Monte Carlo del Mundial 2026 con el calendario y las sedes reales (información conocida antes del torneo)."""
import csv, os, itertools
import numpy as np
from modelo import ROOT, cargar_equipos, cargar_sedes, puntaje, lambdas

FASES = ['Grupos', 'Dieciseisavos', 'Octavos', 'Cuartos', 'Semifinal', 'Final', 'Campeón']
# Dieciseisavos: (partido, local, visitante). '1A' = primero del grupo A, '2B' = segundo, '3:ABCDF' = mejor tercero de esos grupos
R32 = [(73,'2A','2B'),(74,'1E','3:ABCDF'),(75,'1F','2C'),(76,'1C','2F'),(77,'1I','3:CDFGH'),(78,'2E','2I'),
       (79,'1A','3:CEFHI'),(80,'1L','3:EHIJK'),(81,'1D','3:BEFIJ'),(82,'1G','3:AEHIJ'),(83,'2K','2L'),(84,'1H','2J'),
       (85,'1B','3:EFGIJ'),(86,'1J','2H'),(87,'1K','3:DEIJL'),(88,'2D','2G')]
KO = [(89,74,77),(90,73,75),(91,76,78),(92,79,80),(93,83,84),(94,81,82),(95,86,88),(96,85,87),
      (97,89,90),(98,93,94),(99,91,92),(100,95,96),(101,97,98),(102,99,100),(104,101,102)]
SEDE_KO = {73:'Los Ángeles',74:'Boston',75:'Monterrey',76:'Houston',77:'Nueva York/NJ',78:'Dallas',79:'Ciudad de México',
           80:'Atlanta',81:'San Francisco (Santa Clara)',82:'Seattle',83:'Toronto',84:'Los Ángeles',85:'Vancouver',86:'Miami',
           87:'Kansas City',88:'Dallas',89:'Filadelfia',90:'Houston',91:'Nueva York/NJ',92:'Ciudad de México',93:'Dallas',
           94:'Seattle',95:'Atlanta',96:'Vancouver',97:'Boston',98:'Los Ángeles',99:'Miami',100:'Kansas City',101:'Dallas',
           102:'Atlanta',104:'Nueva York/NJ'}
SLOTS3 = [s for _, _, s in R32 if s.startswith('3:')] + [h for _, h, _ in R32 if h.startswith('3:')]

def asignar_terceros(grupos_terceros):
    """Asigna los 8 terceros a los 8 cupos respetando los grupos permitidos de cada cupo.
    Con la combinación real (B,D,E,F,I,J,K,L) da la asignación oficial; en otras usa el primer emparejamiento válido
    (el reglamento usa una tabla fija de 495 combinaciones que no se reproduce aquí)."""
    cupos = [s for _, _, s in R32 if s.startswith('3:')]
    if sorted(grupos_terceros) == list('BDEFIJKL'):   # combinación real 2026: asignación oficial
        return dict(zip(cupos, 'DFEKBIJL'))
    for perm in itertools.permutations(sorted(grupos_terceros)):
        if all(g in c[2:] for g, c in zip(perm, cupos)):
            return dict(zip(cupos, perm))
    raise ValueError(grupos_terceros)

def cargar_calendario():
    M = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'processed', 'mundial2026_partidos.csv'), encoding='utf-8')))
    return [m for m in M if m['fase'] == 'Grupos']

def simular(n=10000, seed=2026, fuerza=None, beta=None):
    """fuerza(equipo, sede) -> puntaje. Devuelve conteos de fase alcanzada por equipo."""
    E = cargar_equipos(); S = cargar_sedes(); cal = cargar_calendario()
    rng = np.random.default_rng(seed)
    equipos = sorted(E); ix = {e: i for i, e in enumerate(equipos)}
    grupos = {}
    for m in cal: grupos.setdefault(m['grupo'], set()).update([m['local'], m['visitante']])
    # lambdas de fase de grupos (fijas por partido)
    gl = []
    for m in cal:
        d = fuerza(E[m['local']], S[m['sede']]) - fuerza(E[m['visitante']], S[m['sede']])
        gl.append((m['grupo'], m['local'], m['visitante'], *lambdas(d, beta)))
    cache = {}
    def lam_ko(a, b, partido):
        k = (a, b, partido)
        if k not in cache:
            s = S[SEDE_KO[partido]]
            cache[k] = lambdas(fuerza(E[a], s) - fuerza(E[b], s), beta)
        return cache[k]
    llega = np.zeros((len(equipos), len(FASES)), dtype=np.int32)
    for _ in range(n):
        pts = {e: [0, 0, 0, rng.random()] for e in equipos}   # puntos, dif, gf, desempate aleatorio
        for g, a, b, la, lb in gl:
            x, y = rng.poisson(la), rng.poisson(lb)
            pts[a][1] += x - y; pts[b][1] += y - x; pts[a][2] += x; pts[b][2] += y
            if x > y: pts[a][0] += 3
            elif y > x: pts[b][0] += 3
            else: pts[a][0] += 1; pts[b][0] += 1
        pos = {}; terceros = []
        for g, ts in grupos.items():
            orden = sorted(ts, key=lambda t: pts[t], reverse=True)
            pos['1' + g], pos['2' + g] = orden[0], orden[1]; terceros.append((pts[orden[2]], g, orden[2]))
        mejores = sorted(terceros, reverse=True)[:8]
        asig = asignar_terceros([g for _, g, _ in mejores]); t_por_g = {g: t for _, g, t in mejores}
        for e in equipos: llega[ix[e], 0] += 1
        gan = {}
        def jugar(a, b, partido):
            la, lb = lam_ko(a, b, partido)
            x, y = rng.poisson(la), rng.poisson(lb)
            if x == y: x, y = rng.poisson(la / 3), rng.poisson(lb / 3)
            if x == y: return a if rng.random() < 0.5 else b
            return a if x > y else b
        for p, h, v in R32:
            a = t_por_g[asig[h]] if h.startswith('3:') else pos[h]
            b = t_por_g[asig[v]] if v.startswith('3:') else pos[v]
            llega[ix[a], 1] += 1; llega[ix[b], 1] += 1
            gan[p] = jugar(a, b, p)
        fase_de = {89: 2, 97: 3, 101: 4, 104: 5}
        f = 2
        for p, x, y in KO:
            f = fase_de.get(p, f)
            a, b = gan[x], gan[y]
            llega[ix[a], f] += 1; llega[ix[b], f] += 1
            gan[p] = jugar(a, b, p)
        llega[ix[gan[104]], 6] += 1
    return {e: llega[ix[e]] / n for e in equipos}

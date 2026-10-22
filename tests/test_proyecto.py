"""Pruebas automáticas: datos, reglas del modelo y del simulador. Correr con:  pytest -q"""
import csv, os, sys
from collections import Counter, defaultdict
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
import modelo
from modelo import prob_1x2, prob_avanza, beta_desde_puntajes, cargar_equipos
from simulacion import asignar_terceros, simular, R32

PARTIDOS = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'processed', 'mundial2026_partidos.csv'), encoding='utf-8')))

# ---------------- datos ----------------
def test_104_partidos_sin_duplicados():
    ids = [int(m['match_id']) for m in PARTIDOS]
    assert sorted(ids) == list(range(1, 105))

def test_partidos_por_fase():
    c = Counter(m['fase'] for m in PARTIDOS)
    assert c == {'Grupos': 72, 'Dieciseisavos': 16, 'Octavos': 8, 'Cuartos': 4, 'Semifinal': 2, 'Tercer lugar': 1, 'Final': 1}

def test_puntos_de_grupo_coinciden_con_tabla_oficial():
    esperado = {'A': [9, 4, 3, 1], 'B': [7, 4, 4, 1], 'C': [7, 7, 3, 0], 'D': [6, 4, 4, 3], 'E': [6, 6, 4, 1], 'F': [7, 5, 4, 0],
                'G': [5, 5, 3, 1], 'H': [7, 3, 2, 2], 'I': [9, 6, 3, 0], 'J': [9, 4, 4, 0], 'K': [7, 5, 4, 0], 'L': [7, 6, 4, 0]}
    pts = defaultdict(int); grupo = {}
    for m in PARTIDOS[:72]:
        a, b, x, y = m['local'], m['visitante'], int(m['goles_local_90']), int(m['goles_visitante_90'])
        grupo[a] = grupo[b] = m['grupo']
        pts[a] += 3 if x > y else 1 if x == y else 0
        pts[b] += 3 if y > x else 1 if x == y else 0
    for g, p in esperado.items():
        assert sorted((pts[t] for t in grupo if grupo[t] == g), reverse=True) == p, g

def test_eliminatorias_tienen_ganador_coherente():
    for m in PARTIDOS[72:]:
        a, b = int(m['goles_local_final']), int(m['goles_visitante_final'])
        assert m['avanza'] in (m['local'], m['visitante'])
        if m['definido_en'] == 'penales':
            assert a == b and m['penales']
        else:
            assert (a > b) == (m['avanza'] == m['local'])
        if m['definido_en'] == '90':
            assert (m['goles_local_90'], m['goles_visitante_90']) == (m['goles_local_final'], m['goles_visitante_final'])

def test_variables_en_rango_y_48_equipos():
    E = cargar_equipos()
    assert len(E) == 48
    for e in E.values():
        for k in ('v_fifa', 'v_top5', 'v_edad', 'v_cont', 'v_forma'):
            assert 1 - 1e-9 <= e[k] <= 10 + 1e-9, (e['equipo'], k, e[k])

def test_elo_solo_usa_partidos_previos_al_corte():
    from elo import elo_history
    _, H = elo_history(os.path.join(ROOT, 'data', 'raw', 'results.csv'), modelo.CORTE)
    assert max(d for hist in H.values() for d, _ in hist) < modelo.CORTE

# ---------------- probabilidades ----------------
@pytest.mark.parametrize('d', [-4, -1.3, 0, 0.7, 3])
def test_probabilidades_suman_uno(d):
    p = prob_1x2(d, 0.26)
    assert abs(sum(p) - 1) < 1e-9 and all(0 <= x <= 1 for x in p)

def test_simetria_y_monotonia():
    w, e, l = prob_1x2(1.0, 0.26); w2, e2, l2 = prob_1x2(-1.0, 0.26)
    assert abs(w - l2) < 1e-9 and abs(e - e2) < 1e-9
    assert prob_1x2(2.0, 0.26)[0] > prob_1x2(1.0, 0.26)[0] > prob_1x2(0, 0.26)[0]
    assert abs(prob_avanza(0, 0.26) - 0.5) < 1e-9

def test_beta_cumple_su_regla():
    b, d95 = beta_desde_puntajes([1, 2, 3, 4, 5, 6, 7, 8])
    assert abs(np.exp(2 * b * d95) - modelo.RATIO_95) < 1e-9

# ---------------- simulador ----------------
def test_terceros_respetan_grupos_permitidos():
    import itertools
    cupos = [s for _, _, s in R32 if s.startswith('3:')]
    for combo in itertools.islice(itertools.combinations('ABCDEFGHIJKL', 8), 0, None, 7):
        asig = asignar_terceros(list(combo))
        assert sorted(asig.values()) == sorted(combo)
        assert all(g in c[2:] for c, g in asig.items())
    assert asignar_terceros(list('BDEFIJKL')) == dict(zip(cupos, 'DFEKBIJL'))   # asignación oficial 2026

def test_simulacion_respeta_formato_del_torneo():
    E = cargar_equipos()
    b, _ = beta_desde_puntajes([modelo.puntaje(e) for e in E.values()])
    sim = simular(n=300, seed=7, fuerza=modelo.puntaje, beta=b)
    tot = np.sum(list(sim.values()), axis=0)
    assert np.allclose(tot, [48, 32, 16, 8, 4, 2, 1])
    for v in sim.values():
        assert all(v[i] >= v[i + 1] - 1e-12 for i in range(6))

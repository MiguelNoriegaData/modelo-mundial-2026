"""Las 5 gráficas del proyecto (PNG estáticos para el README y el notebook)."""
import json, os, csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'graficas'); os.makedirs(FIG, exist_ok=True)
SURF, TXT, TXT2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e6e5e1'
C1, C2, C3 = '#2a78d6', '#eb6834', '#1baf7a'
SEQ = ['#fcfcfb', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
fam = 'Inter' if any('Inter' in f.name for f in font_manager.fontManager.ttflist) else 'DejaVu Sans'
plt.rcParams.update({'font.family': fam, 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': TXT2, 'xtick.color': TXT2,
                     'ytick.color': TXT2, 'axes.facecolor': SURF, 'figure.facecolor': SURF, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.titleweight': 'semibold', 'axes.titlesize': 12, 'axes.titlecolor': TXT,
                     'axes.titlelocation': 'left', 'savefig.dpi': 160, 'savefig.bbox': 'tight'})

def _grid(ax, axis='x'):
    ax.grid(axis=axis, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)

def g1_evolucion(R):
    doce = R['doce']
    def cuenta(filtro):
        xs = [f for f in doce if filtro(f)]; return sum(f['acierto'] == 'sí' for f in xs), len(xs)
    v0_ok = sum(1 for f in doce if f['match_id'] == 28 and f['acierto'] == 'sí') + \
            sum(1 for f in doce if f['pred_v0'] and {'Local': 'L', 'Empate': 'E', 'Visitante': 'V'}[f['pred_v0']] ==
                ('L' if int(f['real_90'].split('-')[0]) > int(f['real_90'].split('-')[1]) else 'V' if int(f['real_90'].split('-')[0]) < int(f['real_90'].split('-')[1]) else 'E'))
    filas = [('Klement (punto de partida)\nfavorito: Países Bajos', None, None, 'eliminado en dieciseisavos'),
             ('v0 · intuición\n18–25 jun', v0_ok, 7, None),
             ('v1 · pesos propios\n25 jun – 12 jul', *cuenta(lambda f: f['version'] == 'v1'), None),
             ('v2 · más peso a la forma\n15–19 jul', *cuenta(lambda f: f['version'] == 'v2'), None)]
    fig, ax = plt.subplots(figsize=(7.5, 3.4)); _grid(ax)
    for i, (lab, ok, n, nota) in enumerate(filas[::-1]):
        if n is None:
            ax.text(0.01, i, nota, va='center', color=TXT2, fontsize=9.5, style='italic'); continue
        ax.barh(i, ok / n, color=C1, height=0.55); ax.barh(i, 1 - ok / n, left=ok / n, color=GRID, height=0.55)
        ax.text(ok / n + 0.02 if ok / n < 0.85 else ok / n - 0.02, i, f'{ok} de {n}', va='center',
                ha='left' if ok / n < 0.85 else 'right', color=TXT if ok / n < 0.85 else SURF, fontsize=10, weight='semibold')
    ax.set_yticks(range(4)); ax.set_yticklabels([f[0] for f in filas[::-1]], fontsize=9)
    ax.set_xlim(0, 1); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title('Aciertos de las predicciones hechas antes de cada partido, por versión', pad=14); ax.set_ylim(-0.5, 3.6)
    fig.text(0.02, -0.04, 'Muestra muy chica (12 partidos únicos; v0 y v1 se traslapan en 6). Acierto = ganador/empate a 90′ en grupos, quién avanza en eliminación.',
            fontsize=8, color=MUTED)
    fig.savefig(os.path.join(FIG, '1_evolucion_modelo.png')); plt.close(fig)

def g2_brier(R):
    modelos = ['v2 reconstruido', 'Solo Elo', 'Solo ranking FIFA']
    g = [R['por_fase']['Grupos'][m]['brier'] for m in modelos]; e = [R['por_fase']['Eliminatorias'][m]['brier'] for m in modelos]
    fig, ax = plt.subplots(figsize=(7.5, 3.6)); _grid(ax)
    y = np.arange(len(modelos)); h = 0.36
    ax.barh(y + h / 2 + 0.01, g, h, color=C1, label='Fase de grupos (72)'); ax.barh(y - h / 2 - 0.01, e, h, color=C2, label='Eliminación (32)')
    for yy, v in zip(y + h / 2, g): ax.text(v + 0.004, yy + 0.01, f'{v:.3f}', va='center', fontsize=9, color=TXT)
    for yy, v in zip(y - h / 2, e): ax.text(v + 0.004, yy - 0.01, f'{v:.3f}', va='center', fontsize=9, color=TXT)
    ax.axvline(2 / 3, color=MUTED, lw=1, ls=(0, (4, 3))); ax.set_ylim(-0.6, 2.95); ax.text(2 / 3 - 0.004, 2.78, 'adivinar 1/3 = 0.667', ha='right', fontsize=8.5, color=MUTED)
    ax.set_yticks(y); ax.set_yticklabels(modelos); ax.set_xlim(0.4, 0.72)
    ax.set_xlabel('Brier score a 90′ (más bajo = mejor)')
    ax.set_title('Precisión probabilística en los 104 partidos')
    lg = ax.legend(frameon=True, loc='lower right', fontsize=9, facecolor=SURF, edgecolor=SURF, framealpha=1)
    fig.savefig(os.path.join(FIG, '2_brier_por_fase.png')); plt.close(fig)

def g3_campeon(R):
    mc = R['montecarlo']; modelos = [('v2 reconstruido', C1, 'o'), ('Solo Elo', C2, 's'), ('Solo ranking FIFA', C3, 'D')]
    eq = set()
    for m, _, _ in modelos: eq |= {e for e, v in sorted(mc[m].items(), key=lambda x: -x[1][6])[:7]}
    eq = sorted(eq, key=lambda e: mc['v2 reconstruido'][e][6])
    fig, ax = plt.subplots(figsize=(7.5, 5)); _grid(ax)
    for i, e in enumerate(eq):
        vals = [mc[m][e][6] for m, _, _ in modelos]; ax.plot([min(vals), max(vals)], [i, i], color=GRID, lw=2, zorder=1)
    for m, c, mk in modelos:
        ax.scatter([mc[m][e][6] for e in eq], range(len(eq)), s=64, color=c, marker=mk, label=m, zorder=3, edgecolor=SURF, lw=2)
    ax.set_yticks(range(len(eq))); ax.set_yticklabels([e + ('  ← campeón real' if e == 'España' else '') for e in eq])
    for t in ax.get_yticklabels():
        if 'campeón' in t.get_text(): t.set_weight('bold'); t.set_color(TXT)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel('Probabilidad de salir campeón (10,000 simulaciones con datos previos al 11-jun)')
    ax.set_title('¿A quién le daba el título cada modelo antes del torneo?')
    ax.legend(frameon=False, loc='lower right', fontsize=9)
    fig.savefig(os.path.join(FIG, '3_probabilidad_campeon.png')); plt.close(fig)

def g4_heatmap(R):
    sim = R['montecarlo']['v2 reconstruido']; real = R['etapa_real']
    fases = ['Dieciseisavos', 'Octavos', 'Cuartos', 'Semifinal', 'Final', 'Campeón']
    eq = sorted([e for e in real if real[e] >= 2], key=lambda e: (-real[e], -sim[e][6]))
    M = np.array([[sim[e][k] for k in range(1, 7)] for e in eq])
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('seq', SEQ)
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect='auto')
    for i, e in enumerate(eq):
        for j in range(6):
            v = M[i, j]; ax.text(j, i, f'{v*100:.0f}', ha='center', va='center', fontsize=8.5, color=SURF if v > 0.55 else TXT)
        r = real[e] - 1
        ax.add_patch(plt.Rectangle((r - 0.5, i - 0.5), 1, 1, fill=False, ec=C2, lw=2.2))
    ax.set_xticks(range(6)); ax.set_xticklabels(['Llegar a\n16avos', 'Octavos', 'Cuartos', 'Semis', 'Final', 'Campeón'], fontsize=9)
    ax.set_yticks(range(len(eq))); ax.set_yticklabels(eq, fontsize=9); ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title('v2 reconstruido: probabilidad (%) de llegar a cada fase\nRecuadro naranja = hasta dónde llegó en realidad (16 equipos de octavos)')
    fig.savefig(os.path.join(FIG, '4_fases_vs_realidad.png')); plt.close(fig)

def g5_calibracion(R):
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'resultados', 'probabilidades_104.csv'), encoding='utf-8')))
    fig, ax = plt.subplots(figsize=(5.6, 5.2)); _grid(ax, 'both')
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls=(0, (4, 3)), label='calibración perfecta')
    bins = np.array([0, .15, .3, .45, .6, 1.0])
    for m, c, mk in [('v2 reconstruido', C1, 'o'), ('Solo Elo', C2, 's')]:
        P, O = [], []
        for r in rows:
            for k, res in zip(('pL', 'pE', 'pV'), 'LEV'):
                P.append(float(r[f'{m} {k}'])); O.append(1 if r['real_90'] == res else 0)
        P, O = np.array(P), np.array(O); idx = np.digitize(P, bins) - 1
        xs = [P[idx == b].mean() for b in range(len(bins) - 1) if (idx == b).sum() >= 5]
        ys = [O[idx == b].mean() for b in range(len(bins) - 1) if (idx == b).sum() >= 5]
        ns = [(idx == b).sum() for b in range(len(bins) - 1) if (idx == b).sum() >= 5]
        ax.plot(xs, ys, color=c, lw=2, marker=mk, ms=8, mec=SURF, mew=2, label=m)
        for x, y, n in zip(xs, ys, ns):
            if m == 'v2 reconstruido': ax.text(x + 0.02, y - 0.045, f'n={n}', fontsize=7.5, color=MUTED)
    ax.set_xlim(0, 0.85); ax.set_ylim(0, 0.85)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0)); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel('Probabilidad que dio el modelo'); ax.set_ylabel('Frecuencia con que pasó')
    ax.set_title('Calibración (312 probabilidades: L/E/V × 104)')
    ax.legend(frameon=False, loc='upper left', fontsize=9)
    fig.savefig(os.path.join(FIG, '5_calibracion.png')); plt.close(fig)

def todas():
    R = json.load(open(os.path.join(ROOT, 'resultados', 'resultados.json'), encoding='utf-8'))
    g1_evolucion(R); g2_brier(R); g3_campeon(R); g4_heatmap(R); g5_calibracion(R)

if __name__ == '__main__':
    todas(); print(sorted(os.listdir(FIG)))

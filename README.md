# ¿Le atinó mi modelo al Mundial 2026?

Evaluación honesta de un modelo de predicción del Mundial 2026 que construí y ajusté **durante** el torneo, comparado contra rivales simples: el ranking FIFA y el Elo.

**Resultado en una línea:** mis 12 predicciones hechas antes de cada partido acertaron 8, pero con probabilidades demasiado extremas. La versión final del modelo, reconstruida con datos previos al torneo, **no le gana de forma clara al ranking FIFA ni al Elo** en los 104 partidos.

![Evolución](graficas/1_evolucion_modelo.png)

## La historia

| Etapa | Qué era | Qué pasó |
|---|---|---|
| **Klement** | Modelo econométrico de Joachim Klement (PIB per cápita, población, temperatura, anfitrión, puntos FIFA) | Su favorito era Países Bajos, eliminado en dieciseisavos (penales contra Marruecos) |
| **v0** (18–25 jun) | Predicciones a intuición, sin puntajes | 4 de 7 |
| **v1** (25 jun) | Fórmula propia: 20% FIFA, 20% jugadores en ligas top 5, 15% edad, 10% continuidad del técnico, 25% forma, 10% clima/altitud | 5 de 9 |
| **v2** (15 jul) | Igual, pero forma 30% y edad 10% | 2 de 2 (semifinal Argentina–Inglaterra y final) |

España fue campeona: le ganó 1-0 a Argentina en tiempo extra (19 de julio, MetLife Stadium).

## Qué se evaluó

1. **Las 12 predicciones reales.** Son las que quedaron registradas antes de cada partido. Se evalúa lo que se predijo en su momento, con los errores de cuenta incluidos (ver abajo).
2. **El modelo v2 reconstruido.** Usa la misma fórmula de la v2, pero cada variable se mide con datos objetivos disponibles antes del 11 de junio de 2026. Se aplicó a los 104 partidos y a una simulación Monte Carlo de 10,000 torneos.

Rivales en los dos casos: **solo ranking FIFA**, **solo Elo** y **adivinar 1/3**.

### Cómo se miden las variables del v2 reconstruido

| Variable | Peso | Regla (escala 1–10) | Fuente |
|---|---|---|---|
| Ranking FIFA | 20% | `10 − 9·(rank−1)/84` | Ranking FIFA vigente al 11-jun-2026 |
| Top 5 | 20% | `1 + 9·%` de la plantilla en la 1a división de ENG/ESP/ITA/GER/FRA 2025-26 | Plantillas oficiales de 26 jugadores; 1,248 jugadores contados uno por uno |
| Edad | 10% | `10 − 3·|edad − 27|` | Edad promedio de las plantillas oficiales (RotoWire) |
| Continuidad | 10% | `1 + 9·min(meses del técnico, 96)/96` | Fecha de nombramiento del técnico |
| Forma | 30% | Cambio de Elo en los 12 meses previos, reescalado a 1–10 | Elo calculado desde cero con la base de partidos internacionales (martj42) |
| Clima | 10% | `10 − 0.3·|T sede − T casa|` − penalización por altitud (CDMX, Guadalajara); estadios con techo climatizado = 22 °C | Normales climáticas aproximadas |

**Paso de puntaje a probabilidades** (la misma regla para todos los modelos, sin calibrar con 2026): los goles de cada equipo siguen una Poisson con `λ = 1.30·exp(±β·d)`, donde d es la diferencia de puntajes. β se fija para que, en un partido muy desigual (percentil 95 de las diferencias), el favorito espere 6 veces más goles que el rival. En eliminación, un empate a 90′ pasa a tiempo extra (λ/3) y luego a penales 50/50.

## Resultados

### 1. Las 12 predicciones reales

- **8 de 12 aciertos.** Los fallos fueron Ecuador–Alemania, Japón–Suecia (v1), Turquía–EE.UU. y México–Inglaterra.
- **Brier promedio de 0.752** en los 11 partidos con puntaje. Adivinar 1/3 da 0.667, el ranking FIFA 0.582 y el v2 reconstruido 0.649. Con la misma regla de conversión, los puntajes del chat daban probabilidades demasiado extremas; por ejemplo, 95% para Alemania contra Ecuador, y ganó Ecuador.
- **Errores aritméticos:** al recalcular, tres totales no coincidían con su propia fórmula, y eso cambiaba el favorito en tres partidos:

  | Partido | Predicción emitida | Con la fórmula bien aplicada | Real |
  |---|---|---|---|
  | Paraguay–Australia | Empate | Australia | 0-0 |
  | México–Inglaterra | México | Inglaterra | 2-3 |
  | Francia–España | España (desempate a criterio) | España | 0-2 |

  El empate en Paraguay–Australia fue acierto gracias al error de cuenta, y México–Inglaterra fue fallo por el error. Los errores se compensan y el saldo es cero.

### 2. Modelo v2 reconstruido en los 104 partidos

| Modelo | Brier (90′) | Log-loss | Aciertos |
|---|---|---|---|
| v2 reconstruido | **0.534** | **0.909** | 60 |
| Solo Elo | 0.534 | 0.917 | 64 |
| Solo ranking FIFA | 0.547 | 0.923 | 64 |
| Adivinar 1/3 | 0.667 | 1.099 | — |

- La diferencia contra el ranking FIFA es de −0.013, con IC 95% por bootstrap de [−0.065, +0.039]. **No es significativa.** Contra el Elo, la diferencia es prácticamente cero.
- El v2 reconstruido **fue el mejor en fase de grupos** (0.515) y **el peor en eliminación** (0.576 contra 0.501 del Elo).
- Si el supuesto de "6 veces más goles" se cambia a 4 o a 9, el orden entre modelos no cambia.
- La calibración es buena: cuando el modelo dice 50%, pasa alrededor del 50% de las veces.

![Brier](graficas/2_brier_por_fase.png)
![Calibración](graficas/5_calibracion.png)

### 3. Simulación Monte Carlo (10,000 torneos)

| Modelo | Favorito antes del torneo | Probabilidad de España campeona |
|---|---|---|
| v2 reconstruido | Francia (14.6%) | 6.6% (5o lugar) |
| Solo ranking FIFA | Argentina (9.0%) | 8.9% |
| Solo Elo | España (28.6%) | **28.6%** |

El v2 reconstruido subestimó a España y a Argentina. La causa es la variable de **forma**: España llegó al torneo con su Elo prácticamente igual que un año antes (Δ 0) y Argentina con −14, así que la forma castiga a quien ya está arriba. Al mismo tiempo, el v2 fue el que mejor describió **hasta dónde llegó cada equipo** (log-verosimilitud media de −1.20, contra −1.23 del Elo y −1.32 del FIFA): vio venir las buenas campañas de Suiza, Bélgica, Noruega y Marruecos.

![Campeón](graficas/3_probabilidad_campeon.png)
![Fases](graficas/4_fases_vs_realidad.png)

## Conclusiones

1. **Acertar 8 de 12 no es lo mismo que predecir bien.** Las probabilidades implícitas eran sobreconfiadas, y la muestra es demasiado chica para separar habilidad de suerte.
2. **Ajustar el modelo sobre la marcha no se tradujo en una ventaja medible.** La v2 reconstruida empata con el Elo y le gana al ranking FIFA por un margen que cabe en el ruido.
3. **Lo que sí aporta el modelo:** ve mejor la fase de grupos y las "sorpresas" de equipos medianos.
4. **Lo que falla:** la forma medida como cambio de Elo penaliza a los equipos que ya estaban arriba. Es justo lo que más importa en eliminación.

## Limitaciones

- **Sesgo retrospectivo.** El análisis se hizo después del torneo, conociendo los resultados. Para limitarlo, todas las reglas se fijaron con criterios previos (no ajustando a los resultados), solo se usaron datos con fecha anterior al 11 de junio, el modelo se congeló en un commit antes de correr la evaluación y se probó la sensibilidad al supuesto clave. Aun así, no es lo mismo que una predicción publicada antes del torneo.
- **Los pesos de la v2 se decidieron viendo partidos del Mundial** (la forma subió a 30% y la edad bajó a 10%). Esto se declara, no se corrige.
- **Muestras chicas:** 12 predicciones reales y 104 partidos. Los intervalos de confianza son anchos.
- **Fechas aproximadas:** las fechas de registro de las predicciones reales son aproximadas, y algunas se hicieron el mismo día del partido.
- **Variables con datos aproximados:**
  - El **clima** usa normales climáticas de referencia, no un índice medido.
  - Algunas **fechas de nombramiento** de técnicos vienen de conocimiento previo y son aproximadas; en `data/raw/tecnicos_nombramiento.csv` se marca cuáles.
  - El **% top 5** toma el club que aparece en la lista oficial de junio.
- **Simplificaciones de la simulación:**
  - Los goles se modelan con Poisson independientes, sin ajuste por empates ni ventaja de local para los anfitriones.
  - Los desempates de grupo no usan el enfrentamiento directo.
  - La asignación de terceros lugares solo replica la tabla oficial para la combinación real; en las demás usa un emparejamiento válido.
- **Klement:** solo se conoce su favorito al título, no predicciones partido por partido, así que no entra en las métricas.

## Cómo reproducir

```bash
pip install numpy pandas matplotlib nbformat nbconvert ipykernel
python src/evaluacion.py      # métricas + Monte Carlo → resultados/
python src/graficas.py        # 5 gráficas → graficas/
jupyter nbconvert --to notebook --execute evaluacion_mundial2026.ipynb
```

## Estructura

```
data/raw/            predicciones del chat, plantillas (clubes por jugador), técnicos, clima, base internacional (martj42)
data/processed/      mundial2026_partidos.csv: 104 partidos + 12 predicciones
src/elo.py           Elo desde cero (fórmula de eloratings.net)
src/modelo.py        v2 reconstruido y regla de probabilidades
src/simulacion.py    Monte Carlo con calendario y sedes reales
src/evaluacion.py    métricas, bootstrap, sensibilidad
src/graficas.py      gráficas
resultados/          resultados.json, probabilidades_104.csv, puntajes_48_equipos.csv
```

## Fuentes

- Resultados: [Excélsior](https://www.excelsior.com.mx/deportes/mundial-2026-resultados-72-partidos-fase-grupos), [Wikipedia](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage), [Ekantipur](https://worldcup.ekantipur.com/schedule), cruzados con [martj42/international_results](https://github.com/martj42/international_results)
- Ranking FIFA: [MLS](https://www.mlssoccer.com/news/fifa-world-rankings-every-team-at-the-world-cup)
- Edades: [RotoWire](https://www.rotowire.com/soccer/article/2026-fifa-world-cup-squad-ages-youngest-oldest-teams-ranked-116813)
- Plantillas: [Wikipedia](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads), [World Cup Ranking](https://worldcupranking.com/blog/world-cup-2026-official-squads-june-3/)
- Técnicos: [World Cup Ranking](https://worldcupranking.com/blog/world-cup-2026-managers-coaches-guide/), notas de nombramiento enlazadas en `data/raw/tecnicos_nombramiento.csv`

*Autor: Miguel — Lic. en Matemáticas Aplicadas (UJED).*

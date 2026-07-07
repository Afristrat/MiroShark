"""
charts.py — ChartFactory : 5 charts signature pour les rapports PDF Bassira.

Chaque méthode retourne des bytes PNG 300 DPI, prêts à être embarqués dans
le pipeline PDF (ReportLab / WeasyPrint). Si les données nécessaires sont
absentes du contexte, un placeholder PNG élégant est retourné (fond cream,
texte centré).

Charts disponibles :
    1. belief_drift()         — Évolution des scores de conviction par round
    2. polymarket_curves()    — Courbes de distribution bullish/bearish
    3. demographic_pyramid()  — Pyramide/bar démographique par segment
    4. influence_leaderboard() — Top-10 agents par score maximal
    5. interaction_network()  — Graphe NetworkX du réseau social des agents

IMPORTANT — champs schema canoniques utilisés (ne pas modifier) :
    AgentState   : agent_id, name, stance, score, message, platform
    Round        : round_idx, agents, summary
    PivotalMoment: round, agent, event, delta_score
    SocialNode   : id, name, group, weight
    SocialEdge   : source, target, weight, sentiment
    DemographicSegment : label, count, pct, dimension
    Outcome      : bullish_pct, bearish_pct, confidence, verdict
"""

from __future__ import annotations

import io
from collections import defaultdict

import matplotlib

# Backend non-interactif DOIT être activé avant tout import pyplot.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import networkx as nx  # noqa: E402

from app.services.report_pdf._style import (  # noqa: E402
    apply_causse_style,
    CAUSSE_PALETTE,
    WI_CHARCOAL,
    WI_CREAM,
    WI_MINT,
    WI_ORANGE,
    WI_SAND,
    WI_TERRA,
)
from app.services.report_pdf.schema import PDFReportContext  # noqa: E402

# Appliquer le style Causse dès l'import du module.
apply_causse_style()


# ─── Helpers internes ──────────────────────────────────────────────────────────


def _fig_to_png(fig: plt.Figure) -> bytes:
    """Sérialise une Figure matplotlib en bytes PNG 300 DPI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    buf.seek(0)
    data = buf.read()
    buf.close()
    plt.close(fig)
    return data


def _placeholder_png(message: str = "Données insuffisantes", width: float = 6.0, height: float = 3.5) -> bytes:
    """
    Retourne un PNG placeholder élégant (fond cream, texte centré en charcoal).

    Utilisé quand les données d'un chart sont absentes ou vides.
    """
    apply_causse_style()
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # Rectangle de fond légèrement plus sombre que le cream
    rect = mpatches.FancyBboxPatch(
        (0.05, 0.15),
        0.9,
        0.7,
        boxstyle="round,pad=0.02",
        linewidth=1,
        edgecolor=WI_SAND,
        facecolor=WI_CREAM,
    )
    ax.add_patch(rect)
    ax.text(
        0.5,
        0.55,
        message,
        ha="center",
        va="center",
        fontsize=10,
        color=WI_CHARCOAL,
        alpha=0.7,
        wrap=True,
    )
    ax.text(
        0.5,
        0.35,
        "— Bassira —",
        ha="center",
        va="center",
        fontsize=7,
        color=WI_TERRA,
        alpha=0.5,
    )
    return _fig_to_png(fig)


# ─── ChartFactory ──────────────────────────────────────────────────────────────


class ChartFactory:
    """
    Fabrique de charts matplotlib pour un PDFReportContext donné.

    Usage ::

        factory = ChartFactory(context)
        png_bytes = factory.belief_drift()

    Chaque méthode est autonome (appelle apply_causse_style() en interne pour
    garantir la consistance même si le style global a été modifié entre deux
    appels). Chaque méthode retourne bytes PNG 300 DPI.
    """

    def __init__(self, context: PDFReportContext) -> None:
        self._ctx = context

    # ── 1. Belief drift ───────────────────────────────────────────────────────

    def belief_drift(self) -> bytes:
        """
        Line chart : évolution du score de conviction par round.

        L99 v2 — classification par SCORE (pas par AgentState.stance string)
        ===================================================================
        Bug fix observé sur sim_76570b79 : tous les agents portaient
        ``stance="neutral"`` dans la trajectoire, ce qui produisait une
        seule courbe « En observation » au lieu des trois promises
        (Adhésion / Résistance / Observation). On reclasse désormais via
        le score numérique au seuil ±0,10 (cohérent avec stance_flow_sankey)
        pour garantir que les trois postures soient toujours tracées.

        X = round_idx (Round.round_idx)
        Y = score moyen par posture-via-score à ce round
        Seuils : score > +0,10 → Adhésion, < -0,10 → Résistance, sinon Observation

        Callouts verticaux sur les PivotalMoment (PivotalMoment.round,
        PivotalMoment.agent, PivotalMoment.event).

        Si la trajectoire est absente ou vide → placeholder PNG.
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return _placeholder_png("Trajectoire non disponible\n(belief drift)")

        rounds = sorted(ctx.trajectory.rounds, key=lambda r: r.round_idx)

        # ── Collecte : score moyen par posture (classifiée via score), par round ──
        # Classification : score > +0,10 → Adhésion, < -0,10 → Résistance, sinon Observation.
        # On collecte les scores de chaque bucket SÉPARÉMENT de toute notion
        # d'agent.stance string, qui est régulièrement à "neutral" pour tous.
        posture_scores: dict[str, dict[int, list[float]]] = {
            "Adhésion":       defaultdict(list),
            "Résistance":     defaultdict(list),
            "En observation": defaultdict(list),
        }
        for rnd in rounds:
            for agent in rnd.agents:
                if agent.score > 0.10:
                    posture_scores["Adhésion"][rnd.round_idx].append(agent.score)
                elif agent.score < -0.10:
                    posture_scores["Résistance"][rnd.round_idx].append(agent.score)
                else:
                    posture_scores["En observation"][rnd.round_idx].append(agent.score)

        round_indices = sorted({r.round_idx for r in rounds})
        if not round_indices:
            return _placeholder_png("Aucun round\n(belief drift)")

        # ── Figure ──
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.set_title("Évolution des convictions au fil des rounds", pad=10)
        ax.set_xlabel("Round de discussion")
        ax.set_ylabel("Score moyen de conviction")

        # Mapping posture → couleur cohérente (vert/rouge/sable)
        _POSTURE_COLOR = {
            "Adhésion":       WI_MINT,
            "Résistance":     WI_TERRA,
            "En observation": WI_ORANGE,
        }

        # Pour chaque posture, tracer une courbe (en plottant 0 quand bucket vide
        # pour ne pas casser la lisibilité visuelle).
        for posture, round_data in posture_scores.items():
            xs, ys = [], []
            for idx in round_indices:
                scores = round_data.get(idx, [])
                if scores:
                    xs.append(idx)
                    ys.append(sum(scores) / len(scores))
            if xs:
                ax.plot(
                    xs, ys,
                    marker="o", markersize=4,
                    label=posture,
                    color=_POSTURE_COLOR[posture],
                    linewidth=1.5,
                )

        # Callouts pivotal_moments (déduplication par (round, agent) pour ne pas
        # tracer 10 fois la même verticale quand un agent bascule plusieurs fois
        # au même round).
        seen_pivot_keys: set = set()
        for pm in ctx.pivotal_moments:
            key = (pm.round, pm.agent)
            if key in seen_pivot_keys:
                continue
            seen_pivot_keys.add(key)
            ax.axvline(x=pm.round, color=WI_TERRA, linestyle="--", linewidth=0.8, alpha=0.6)
            ymax = ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else 1.0
            label_text = (pm.agent or "Pivot")[:12]
            ax.text(
                pm.round + 0.05,
                ymax * 0.92,
                label_text,
                fontsize=6,
                color=WI_TERRA,
                rotation=90,
                va="top",
                alpha=0.8,
            )

        ax.legend(loc="best", ncol=3, fontsize=7)
        ax.set_xticks(round_indices)
        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 2. Polymarket curves ──────────────────────────────────────────────────

    def polymarket_curves(self) -> bytes:
        """
        Courbes bullish vs bearish par round (style marché prédictif).

        Utilise le pourcentage d'agents bullish/bearish par round calculé
        depuis la trajectoire (AgentState.stance). Si l'Outcome fournit
        les valeurs finales (bullish_pct / bearish_pct), elles sont annotées.

        Si données insuffisantes → placeholder PNG.
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return _placeholder_png("Trajectoire non disponible\n(polymarket curves)")

        rounds = sorted(ctx.trajectory.rounds, key=lambda r: r.round_idx)

        xs: list[int] = []
        bullish_series: list[float] = []
        bearish_series: list[float] = []
        neutral_series: list[float] = []

        for rnd in rounds:
            if not rnd.agents:
                continue
            total = len(rnd.agents)
            bullish = sum(1 for a in rnd.agents if a.stance.lower() in ("bullish", "bull", "positive", "optimistic"))
            bearish = sum(1 for a in rnd.agents if a.stance.lower() in ("bearish", "bear", "negative", "pessimistic"))
            neutral = total - bullish - bearish
            xs.append(rnd.round_idx)
            bullish_series.append(100.0 * bullish / total)
            bearish_series.append(100.0 * bearish / total)
            neutral_series.append(100.0 * max(neutral, 0) / total)

        if not xs:
            return _placeholder_png("Aucun agent dans les rounds\n(polymarket curves)")

        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.set_title("Évolution comparative adhésion / résistance par round", pad=10)
        ax.set_xlabel("Round")
        ax.set_ylabel("% des agents")
        ax.set_ylim(0, 105)

        ax.plot(xs, bullish_series, marker="o", markersize=4, label="Adhésion", color=WI_MINT, linewidth=2)
        ax.plot(xs, bearish_series, marker="o", markersize=4, label="Résistance", color=WI_TERRA, linewidth=2)
        ax.plot(xs, neutral_series, marker="o", markersize=4, label="En observation", color=WI_SAND, linewidth=1.5, linestyle="--")

        ax.fill_between(xs, bullish_series, alpha=0.08, color=WI_MINT)
        ax.fill_between(xs, bearish_series, alpha=0.08, color=WI_TERRA)

        # Annotation valeur finale depuis outcome si disponible
        if ctx.outcome is not None:
            ax.annotate(
                f"Adhésion finale : {ctx.outcome.bullish_pct:.0f} %",
                xy=(xs[-1], bullish_series[-1]),
                xytext=(xs[-1] - 0.5, bullish_series[-1] + 6),
                fontsize=6,
                color=WI_MINT,
                arrowprops={"arrowstyle": "->", "color": WI_MINT, "lw": 0.7},
            )
            ax.annotate(
                f"Résistance finale : {ctx.outcome.bearish_pct:.0f} %",
                xy=(xs[-1], bearish_series[-1]),
                xytext=(xs[-1] - 0.5, bearish_series[-1] - 10),
                fontsize=6,
                color=WI_TERRA,
                arrowprops={"arrowstyle": "->", "color": WI_TERRA, "lw": 0.7},
            )

        ax.legend(loc="best")
        ax.set_xticks(xs)
        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 3. Demographic pyramid ────────────────────────────────────────────────

    def demographic_pyramid(self) -> bytes:
        """
        Pyramide démographique ou bar chart par segment.

        Si la dimension 'genre'/'gender' est présente dans les segments,
        affiche une pyramide horizontale (femmes à gauche, hommes à droite).
        Sinon, affiche un bar chart horizontal simple groupé par dimension.

        Utilise : DemographicSegment.label, pct, count, dimension.

        Si données absentes → placeholder PNG.
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.demographics is None or not ctx.demographics.segments:
            return _placeholder_png("Données démographiques non disponibles\n(demographic pyramid)")

        segments = ctx.demographics.segments

        # Tenter la pyramide genre
        genre_dims = {"genre", "gender", "sex", "sexe"}
        genre_segs = [s for s in segments if s.dimension.lower() in genre_dims]

        if len(genre_segs) >= 2:
            return self._draw_gender_pyramid(genre_segs)
        else:
            return self._draw_segment_bars(segments)

    def _draw_gender_pyramid(self, genre_segs: list) -> bytes:
        """Pyramide horizontale femmes/hommes."""
        apply_causse_style()

        # On cherche les labels qui ressemblent à homme/femme
        fem_keywords = {"femme", "female", "f", "women", "woman", "féminin"}
        masc_keywords = {"homme", "male", "m", "men", "man", "masculin"}

        left_segs = [s for s in genre_segs if s.label.lower() in fem_keywords]
        right_segs = [s for s in genre_segs if s.label.lower() in masc_keywords]

        if not left_segs and not right_segs:
            # Fallback : premier segment à gauche, reste à droite
            left_segs = genre_segs[:1]
            right_segs = genre_segs[1:]

        # Valeurs
        left_val = left_segs[0].pct if left_segs else 0.0
        right_val = right_segs[0].pct if right_segs else 0.0
        left_label = left_segs[0].label if left_segs else "–"
        right_label = right_segs[0].label if right_segs else "–"

        fig, ax = plt.subplots(figsize=(5, 2.5))
        ax.set_title("Répartition démographique par genre", pad=8)

        ax.barh([0], [-left_val], color=WI_ORANGE, alpha=0.85, label=left_label)
        ax.barh([0], [right_val], color=WI_MINT, alpha=0.85, label=right_label)
        ax.axvline(0, color=WI_CHARCOAL, linewidth=0.8)
        ax.set_yticks([])
        ax.set_xlabel("% agents")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{abs(x):.0f}%"))

        ax.text(-left_val / 2, 0, f"{left_val:.1f}%", ha="center", va="center",
                fontsize=8, color="white", fontweight="bold")
        ax.text(right_val / 2, 0, f"{right_val:.1f}%", ha="center", va="center",
                fontsize=8, color="white", fontweight="bold")

        ax.legend(loc="upper right", fontsize=7)
        fig.tight_layout()
        return _fig_to_png(fig)

    def _draw_segment_bars(self, segments: list) -> bytes:
        """Bar chart horizontal pour segments démographiques généraux."""
        apply_causse_style()

        # Grouper par dimension pour couleur
        dims = list({s.dimension for s in segments if s.dimension})
        dim_colors = {d: CAUSSE_PALETTE[i % len(CAUSSE_PALETTE)] for i, d in enumerate(dims)}

        labels = [s.label for s in segments]
        values = [s.pct for s in segments]
        colors = [dim_colors.get(s.dimension, WI_ORANGE) for s in segments]

        fig, ax = plt.subplots(figsize=(6, max(2.5, len(segments) * 0.5)))
        ax.set_title("Répartition démographique", pad=8)

        bars = ax.barh(labels, values, color=colors, alpha=0.85)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%",
                va="center",
                fontsize=7,
                color=WI_CHARCOAL,
            )

        ax.set_xlabel("% agents")
        ax.set_xlim(0, max(values) * 1.2 if values else 100)

        # Légende dimensions
        if dims:
            patches = [mpatches.Patch(color=dim_colors[d], label=d or "–") for d in dims]
            ax.legend(handles=patches, loc="lower right", fontsize=6)

        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 4. Influence leaderboard ──────────────────────────────────────────────

    def influence_leaderboard(self) -> bytes:
        """
        Bar chart horizontal : top-10 agents par score maximal.

        Agrège le score max de chaque agent (AgentState.name, AgentState.score)
        sur l'ensemble de la trajectoire. Coloré par stance dominante.

        Si trajectoire absente ou vide → placeholder PNG.
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return _placeholder_png("Trajectoire non disponible\n(influence leaderboard)")

        # L99 v2 — Lookup ordinal → nom propre depuis agent_profiles
        profile_name_by_ordinal: dict[str, str] = {}
        for idx, profile in enumerate(ctx.agent_profiles or []):
            if profile.name and not profile.name.isdigit():
                profile_name_by_ordinal[str(idx)] = profile.name

        # Agréger score max et stance dominante par agent key (preference name lisible)
        agent_max_score: dict[str, float] = {}
        agent_stance_count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        agent_display: dict[str, str] = {}

        for rnd in ctx.trajectory.rounds:
            for agent in rnd.agents:
                key = agent.agent_id or agent.name
                if not key:
                    continue
                # Résolution stricte du nom propre
                if agent.name and not agent.name.isdigit():
                    agent_display[key] = agent.name
                elif key in profile_name_by_ordinal:
                    agent_display[key] = profile_name_by_ordinal[key]
                elif key not in agent_display:
                    agent_display[key] = f"Agent #{key}"
                if key not in agent_max_score or agent.score > agent_max_score[key]:
                    agent_max_score[key] = agent.score
                agent_stance_count[key][agent.stance] += 1

        if not agent_max_score:
            return _placeholder_png("Aucun agent dans la trajectoire\n(influence leaderboard)")

        # Top 10 par score max décroissant — projeter sur les noms display
        top10 = sorted(agent_max_score.items(), key=lambda kv: kv[1], reverse=True)[:10]
        names = [agent_display.get(k, k) for k, _ in top10]
        scores = [item[1] for item in top10]

        # Stance dominante pour la couleur
        stance_color_map = {
            "bullish": WI_MINT,
            "bull": WI_MINT,
            "positive": WI_MINT,
            "optimistic": WI_MINT,
            "bearish": WI_TERRA,
            "bear": WI_TERRA,
            "negative": WI_TERRA,
            "pessimistic": WI_TERRA,
        }

        bar_colors = []
        for key, _ in top10:
            stance_counts = agent_stance_count.get(key, {})
            dominant = max(stance_counts, key=lambda s: stance_counts[s]) if stance_counts else "neutral"
            bar_colors.append(stance_color_map.get(dominant.lower(), WI_ORANGE))

        fig, ax = plt.subplots(figsize=(7.0, max(3.0, len(names) * 0.45)))
        ax.set_title("Top agents par conviction maximale atteinte", pad=8)

        # Ordre croissant pour la lisibilité (meilleur en haut)
        ypos = range(len(names))
        bars = ax.barh(list(ypos), scores[::-1], color=list(reversed(bar_colors)), alpha=0.85)
        ax.set_yticks(list(ypos))
        ax.set_yticklabels([n[:32] for n in reversed(names)], fontsize=7)
        ax.set_xlabel("Conviction maximale")

        for bar, val in zip(bars, reversed(scores)):
            ax.text(
                bar.get_width() + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}",
                va="center",
                fontsize=6.5,
                color=WI_CHARCOAL,
            )

        # Légende posture (vocabulaire C-level, plus de bullish/bearish)
        legend_patches = [
            mpatches.Patch(color=WI_MINT, label="Adhésion"),
            mpatches.Patch(color=WI_TERRA, label="Résistance"),
            mpatches.Patch(color=WI_ORANGE, label="En observation"),
        ]
        ax.legend(handles=legend_patches, loc="lower right", fontsize=6)

        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 5. Influence × Posture matrix (quadrant tactique C-level) ─────────────

    def influence_posture_matrix(self) -> bytes:
        """
        Scatter plot 2D : axe X = influence (variations de score induites),
        axe Y = score final. Quatre quadrants :
            Champions          (haut + droite)  — influence forte + adhésion
            Sceptiques bruyants (haut + gauche)  — influence forte + résistance
            Adoptants discrets  (bas  + droite)  — influence faible + adhésion
            Indifférents        (bas  + gauche)  — influence faible + résistance

        L99 v2 — Améliorations :
        - Labels d'agents plus longs (22 chars au lieu de 14) pour lisibilité
        - Résolution prioritaire du nom propre via agent.name (pas agent_id)
        - Si name est purement numérique (artefact moteur), tente fallback sur
          agent_profiles[ordinal].name pour reconstituer le vrai nom
        - Annotations quadrants avec position fixe (plus de jitter sur xlim/ylim)

        Lecture C-level : le CEO sait immédiatement sur qui investir son
        temps de conviction (sceptiques bruyants à convertir) et qui
        amplifier (champions à promouvoir comme témoins).
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return _placeholder_png("Trajectoire indisponible\n(matrice influence × posture)")

        # Lookup ordinal → nom propre depuis agent_profiles (L99 v2 fix)
        profile_name_by_ordinal: dict[str, str] = {}
        for idx, profile in enumerate(ctx.agent_profiles or []):
            if profile.name and not profile.name.isdigit():
                profile_name_by_ordinal[str(idx)] = profile.name

        # Score final + variations cumulées par agent
        agent_final: dict[str, float] = {}
        agent_influence: dict[str, float] = {}
        agent_name: dict[str, str] = {}

        prev_scores: dict[str, float] = {}
        for rnd in ctx.trajectory.rounds:
            for a in rnd.agents:
                key = a.agent_id or a.name
                if not key:
                    continue
                # Préférence stricte au nom non-numérique
                if a.name and not a.name.isdigit():
                    agent_name[key] = a.name
                elif key in profile_name_by_ordinal:
                    agent_name[key] = profile_name_by_ordinal[key]
                elif key not in agent_name:
                    agent_name[key] = a.name or key
                if key in prev_scores:
                    agent_influence[key] = agent_influence.get(key, 0.0) + abs(a.score - prev_scores[key])
                prev_scores[key] = a.score
                agent_final[key] = a.score

        if not agent_final:
            return _placeholder_png("Aucun agent\n(matrice influence × posture)")

        # Garde les 20 agents les plus actifs (influence cumulée la plus haute)
        sorted_keys = sorted(agent_influence.keys(), key=lambda k: agent_influence.get(k, 0), reverse=True)[:20]
        if not sorted_keys:
            sorted_keys = list(agent_final.keys())[:20]

        xs = [agent_influence.get(k, 0.0) for k in sorted_keys]
        ys = [agent_final.get(k, 0.0) for k in sorted_keys]
        labels = [agent_name.get(k, k)[:22] for k in sorted_keys]

        # Couleur par quadrant
        mean_x = sum(xs) / len(xs) if xs else 0
        colors = []
        for x, y in zip(xs, ys):
            if y >= 0 and x >= mean_x:
                colors.append(WI_MINT)         # Champions
            elif y < 0 and x >= mean_x:
                colors.append(WI_TERRA)        # Sceptiques bruyants
            elif y >= 0:
                colors.append(WI_SAND)         # Adoptants discrets
            else:
                colors.append(WI_CHARCOAL)     # Indifférents/silencieux

        fig, ax = plt.subplots(figsize=(7.5, 5.0))
        ax.set_title("Matrice Influence × Posture finale", pad=10)

        # Axes croisés au centre (mean(x), 0)
        ax.axvline(x=mean_x, color=WI_CHARCOAL, linestyle="--", linewidth=0.6, alpha=0.5)
        ax.axhline(y=0,      color=WI_CHARCOAL, linestyle="--", linewidth=0.6, alpha=0.5)

        ax.scatter(xs, ys, c=colors, s=90, alpha=0.85, edgecolors="white", linewidth=0.8)
        for x, y, lab in zip(xs, ys, labels):
            ax.annotate(lab, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=6.5, color=WI_CHARCOAL)

        # Annotations quadrant — positions fixes basées sur xlim/ylim après scatter
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        # Pad léger pour éviter de toucher les bords
        x_left  = xlim[0] + 0.03 * (xlim[1] - xlim[0])
        x_right = xlim[1] - 0.03 * (xlim[1] - xlim[0])
        y_top   = ylim[1] - 0.05 * (ylim[1] - ylim[0])
        y_bot   = ylim[0] + 0.05 * (ylim[1] - ylim[0])

        ax.text(x_right, y_top, "Champions",            ha="right", va="top",    fontsize=8, color=WI_MINT,     alpha=0.85, fontweight="bold")
        ax.text(x_left,  y_top, "Sceptiques bruyants",  ha="left",  va="top",    fontsize=8, color=WI_TERRA,    alpha=0.85, fontweight="bold")
        ax.text(x_right, y_bot, "Adoptants discrets",   ha="right", va="bottom", fontsize=8, color=WI_SAND,     alpha=0.95, fontweight="bold")
        ax.text(x_left,  y_bot, "Indifférents",         ha="left",  va="bottom", fontsize=8, color=WI_CHARCOAL, alpha=0.85, fontweight="bold")

        ax.set_xlabel("Influence cumulée (somme des |Δ score| sur la trajectoire)")
        ax.set_ylabel("Posture finale (score)")

        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 6. Cinétique de bascule (Sankey simplifié 3 colonnes) ─────────────────

    def stance_flow_sankey(self) -> bytes:
        """
        Sankey simplifié à 3 colonnes (Début / Milieu / Fin) qui montre comment
        les agents migrent entre les trois postures Adhésion / Résistance /
        En observation au fil de la simulation.

        Lecture C-level : la cinétique de conversion. À quel moment la majorité
        bascule ? Y a-t-il des reculs (Adhésion → Résistance) qui signalent
        un incident ?
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return _placeholder_png("Trajectoire indisponible\n(cinétique de bascule)")

        rounds = ctx.trajectory.rounds
        n = len(rounds)
        snapshots_idx = [0, n // 2, n - 1]
        snapshot_labels = ["Début", "Milieu", "Fin"]

        # Compter agents par posture à chaque snapshot
        def _classify(agents):
            adhesion = sum(1 for a in agents if a.score >  0.10)
            resistance = sum(1 for a in agents if a.score < -0.10)
            observation = len(agents) - adhesion - resistance
            return [adhesion, resistance, observation]

        counts = [_classify(rounds[i].agents) for i in snapshots_idx]

        fig, ax = plt.subplots(figsize=(7, 4.0))
        ax.set_title("Cinétique de bascule des postures (Début → Milieu → Fin)", pad=10)
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(-0.05, 1.05)
        ax.axis("off")

        category_colors = [WI_MINT, WI_TERRA, WI_SAND]
        category_labels = ["Adhésion", "Résistance", "En observation"]

        # Empiler les blocs proportionnels par snapshot
        bar_width = 0.18
        block_positions: list[list[tuple[float, float]]] = []  # (y_low, y_high) par catégorie
        for col_idx, col_counts in enumerate(counts):
            total = sum(col_counts) or 1
            y = 0.0
            positions = []
            for cat_idx, cnt in enumerate(col_counts):
                height = cnt / total
                ax.add_patch(mpatches.Rectangle(
                    (col_idx - bar_width / 2, y),
                    bar_width,
                    height,
                    facecolor=category_colors[cat_idx],
                    edgecolor="white",
                    linewidth=0.8,
                    alpha=0.9,
                ))
                if height > 0.06:
                    ax.text(col_idx, y + height / 2, f"{int(cnt)}", ha="center", va="center", fontsize=7, color="white", fontweight="bold")
                positions.append((y, y + height))
                y += height
            block_positions.append(positions)
            ax.text(col_idx, -0.04, snapshot_labels[col_idx], ha="center", va="top", fontsize=8, color=WI_CHARCOAL, fontweight="bold")

        # Tirer des bandes de flux entre snapshots (approximation Sankey)
        for src in range(len(snapshots_idx) - 1):
            for cat in range(3):
                y1_low, y1_high = block_positions[src][cat]
                y2_low, y2_high = block_positions[src + 1][cat]
                xs = [src + bar_width / 2, src + 1 - bar_width / 2]
                ys_low  = [y1_low,  y2_low]
                ys_high = [y1_high, y2_high]
                ax.fill_between(xs, ys_low, ys_high, color=category_colors[cat], alpha=0.18, linewidth=0)

        # Légende
        legend_patches = [mpatches.Patch(color=c, label=ln) for c, ln in zip(category_colors, category_labels)]
        ax.legend(handles=legend_patches, loc="upper right", fontsize=7, framealpha=0.9)

        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 7. Heatmap d'engagement agent × round ─────────────────────────────────

    def agent_engagement_heatmap(self) -> bytes:
        """
        Grille colorée agent × round. Permet d'identifier les agents
        passifs (lignes pâles), les champions persistants (vert intense),
        les résistants persistants (rouge intense) et les bascules tardives.

        Lecture C-level : qui s'engage quand. Précieux pour distinguer
        les "convaincus de la première heure" des "convaincus tardifs" —
        leur valeur de témoignage interne n'est pas la même.
        """
        apply_causse_style()

        ctx = self._ctx
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return _placeholder_png("Trajectoire indisponible\n(heatmap engagement)")

        rounds = ctx.trajectory.rounds

        # L99 v2 — Lookup ordinal → nom propre
        profile_name_by_ordinal: dict[str, str] = {}
        for idx, profile in enumerate(ctx.agent_profiles or []):
            if profile.name and not profile.name.isdigit():
                profile_name_by_ordinal[str(idx)] = profile.name

        # Collecter scores par agent × round
        agent_scores: dict[str, dict[int, float]] = {}
        agent_name: dict[str, str] = {}
        for rnd in rounds:
            for a in rnd.agents:
                key = a.agent_id or a.name
                if not key:
                    continue
                if a.name and not a.name.isdigit():
                    agent_name[key] = a.name
                elif key in profile_name_by_ordinal:
                    agent_name[key] = profile_name_by_ordinal[key]
                elif key not in agent_name:
                    agent_name[key] = a.name or key
                agent_scores.setdefault(key, {})[rnd.round_idx] = a.score

        if not agent_scores:
            return _placeholder_png("Aucun agent\n(heatmap engagement)")

        # Top 20 agents par activité (somme des |score|)
        ranked = sorted(
            agent_scores.keys(),
            key=lambda k: sum(abs(v) for v in agent_scores[k].values()),
            reverse=True,
        )[:20]

        round_indices = sorted({r.round_idx for r in rounds})
        # Matrice (n_agents, n_rounds)
        import numpy as np  # local import pour éviter pénalité au boot
        matrix = np.zeros((len(ranked), len(round_indices)))
        for i, agent_key in enumerate(ranked):
            for j, ridx in enumerate(round_indices):
                matrix[i, j] = agent_scores[agent_key].get(ridx, 0.0)

        fig, ax = plt.subplots(figsize=(7, max(3.0, len(ranked) * 0.25)))
        ax.set_title("Engagement agent × round (vert = adhésion, rouge = résistance)", pad=10)

        # Colormap divergente custom : rouge → blanc → vert (WI_TERRA → cream → WI_MINT)
        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list("posture", [WI_TERRA, WI_CREAM, WI_MINT], N=256)

        vmax = max(abs(matrix.min()), abs(matrix.max()), 0.5)
        im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=-vmax, vmax=vmax, interpolation="nearest")

        ax.set_yticks(range(len(ranked)))
        ax.set_yticklabels([agent_name.get(k, k)[:26] for k in ranked], fontsize=6)
        # Ticks rounds : pas trop de labels (1 sur 5)
        tick_step = max(1, len(round_indices) // 12)
        ax.set_xticks(range(0, len(round_indices), tick_step))
        ax.set_xticklabels([str(round_indices[i]) for i in range(0, len(round_indices), tick_step)], fontsize=6)
        ax.set_xlabel("Round de discussion")

        cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
        cbar.set_label("Score de posture", fontsize=7)
        cbar.ax.tick_params(labelsize=6)

        fig.tight_layout()
        return _fig_to_png(fig)

    # ── 8. Interaction network (déjà existant — coalition map) ────────────────

    def interaction_network(self) -> bytes:
        """
        Graphe NetworkX des interactions entre agents.

        Nœuds : SocialNode (id, name, group, weight)
        Arêtes : SocialEdge (source, target, weight, sentiment)
        Layout : nx.spring_layout(seed=42)
        Couleur nœud : par group (SocialNode.group) → CAUSSE_PALETTE
        Taille nœud : proportionnelle à SocialNode.weight

        Si réseau social absent ou vide → placeholder PNG.
        """
        apply_causse_style()

        ctx = self._ctx
        if (
            ctx.social_network is None
            or not ctx.social_network.nodes
        ):
            return _placeholder_png("Réseau social non disponible\n(interaction network)")

        nodes = ctx.social_network.nodes
        edges = ctx.social_network.edges

        # Construire le graphe
        G = nx.Graph()
        for node in nodes:
            G.add_node(node.id, name=node.name, group=node.group, weight=node.weight)

        for edge in edges:
            if edge.source and edge.target:
                G.add_edge(edge.source, edge.target, weight=edge.weight, sentiment=edge.sentiment)

        if len(G.nodes) == 0:
            return _placeholder_png("Graphe vide\n(interaction network)")

        # Layout déterministe
        pos = nx.spring_layout(G, seed=42, k=0.8)

        # Couleurs par group
        groups = list({d.get("group", "") for _, d in G.nodes(data=True)})
        group_color_map = {g: CAUSSE_PALETTE[i % len(CAUSSE_PALETTE)] for i, g in enumerate(groups)}
        node_colors = [group_color_map.get(G.nodes[n].get("group", ""), WI_ORANGE) for n in G.nodes]

        # Tailles proportionnelles au weight (normalisées)
        raw_weights = [G.nodes[n].get("weight", 1.0) for n in G.nodes]
        max_w = max(raw_weights) if raw_weights else 1.0
        node_sizes = [max(80, 600 * (w / max_w)) for w in raw_weights]

        # Couleurs des arêtes par sentiment
        sentiment_color_map = {
            "positive": WI_MINT,
            "negative": WI_TERRA,
            "neutral": WI_SAND,
        }
        edge_colors = [
            sentiment_color_map.get(G.edges[e].get("sentiment", "neutral"), WI_SAND)
            for e in G.edges
        ]
        edge_weights_raw = [G.edges[e].get("weight", 1.0) for e in G.edges]
        max_ew = max(edge_weights_raw) if edge_weights_raw else 1.0
        edge_widths = [max(0.5, 3.0 * (w / max_ew)) for w in edge_weights_raw]

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.set_title("Réseau d'interactions entre agents", pad=10)
        ax.axis("off")

        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edge_color=edge_colors,
            width=edge_widths,
            alpha=0.5,
        )
        nx.draw_networkx_nodes(
            G, pos, ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.85,
        )

        # Labels : name si disponible, sinon id (tronqué)
        labels = {n: (G.nodes[n].get("name") or n)[:14] for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=5, font_color=WI_CHARCOAL)

        # Légende groupes
        if groups:
            patches = [
                mpatches.Patch(color=group_color_map[g], label=g[:18] or "–")
                for g in groups
                if g
            ]
            if patches:
                ax.legend(handles=patches, loc="lower left", fontsize=6, title="Groupes")

        fig.tight_layout()
        return _fig_to_png(fig)

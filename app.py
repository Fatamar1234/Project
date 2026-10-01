"""MovieLens dashboard — four required Week 4 charts.

Build notes (keep for next week's write-up):
- Prompt: answer Q1–Q4 as written with charts; CSV from CUNY Tech Prep movie_ratings.csv.
- First pass already had Plotly + Streamlit; this pass makes Q4 show floors 50 and 150
  side by side (the actual question) instead of only a slider, and labels Q3 as
  *release year*, not year rated.
- Chart choices: sorted horizontal bars for genres (too many slices for a pie),
  line for mean rating by release year, grouped bars for top-5 under two floors.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "movie_ratings.csv"

st.set_page_config(
    page_title="MovieLens Dashboard",
    page_icon="🎬",
    layout="wide",
)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FAFAFA"),
    margin=dict(l=10, r=10, t=48, b=10),
)


@st.cache_data
def load_ratings() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating", "movie_id", "title"])
    df["genres"] = df["genres"].fillna("unknown").astype(str)
    return df


def explode_genres(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per (original row, genre). Pipe-separated tags become separate rows."""
    out = frame.copy()
    out["genre"] = out["genres"].str.split("|")
    out = out.explode("genre")
    out["genre"] = out["genre"].str.strip()
    return out[out["genre"].ne("") & out["genre"].notna()]


def top_movies(stats: pd.DataFrame, floor: int, genre_ids=None) -> pd.DataFrame:
    work = stats
    if genre_ids is not None:
        work = work[work["movie_id"].isin(genre_ids)]
    eligible = work[work["n_ratings"] >= floor]
    return eligible.sort_values(
        ["avg_rating", "n_ratings"], ascending=[False, False]
    ).head(5)


def ranked_bar(frame: pd.DataFrame, floor: int):
    if frame.empty:
        return None
    plot = frame.sort_values("avg_rating", ascending=True)
    fig = px.bar(
        plot,
        x="avg_rating",
        y="title",
        orientation="h",
        title=f"Top 5 with at least {floor} ratings",
        labels={"avg_rating": "Mean rating (1–5)", "title": "Movie"},
        hover_data={"n_ratings": True, "avg_rating": ":.3f"},
        text=plot["avg_rating"].map(lambda x: f"{x:.2f}"),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**CHART_LAYOUT, height=340)
    fig.update_xaxes(range=[3.5, 5])
    return fig


ratings = load_ratings()
movies = ratings.drop_duplicates(subset=["movie_id"]).copy()

years_present = movies["year"].dropna()
year_min = int(years_present.min())
year_max = int(years_present.max())

st.title("MovieLens Dashboard")
st.caption(
    "Source: GroupLens MovieLens (`movie_ratings.csv`, 100,000 ratings). "
    "Each chart answers one of the four Week 4 questions as written."
)

with st.sidebar:
    st.header("Filters")
    year_range = st.slider(
        "Movie release years",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
        help="Uses the movie's release year, not the year the rating was submitted.",
    )
    min_year_n = st.slider(
        "Hide sparse years (Q3)",
        min_value=1,
        max_value=200,
        value=30,
        help="Years with fewer ratings than this are omitted from the time-series so early noisy years don't dominate the line.",
    )
    extra_floor = st.slider(
        "Custom ratings floor (Q4)",
        min_value=10,
        max_value=300,
        value=50,
        step=10,
        help="The assignment asks for 50 and 150; this slider lets you try other floors.",
    )
    all_genres = sorted(explode_genres(movies)["genre"].unique())
    selected_genres = st.multiselect(
        "Restrict top movies to these genres (optional)",
        options=all_genres,
        default=[],
        help="Leave empty to include every genre. Applies to Question 4 only.",
    )

in_year = ratings["year"].between(year_range[0], year_range[1]) | ratings["year"].isna()
filtered = ratings[in_year]
filtered_movies = filtered.drop_duplicates(subset=["movie_id"])

c1, c2, c3 = st.columns(3)
c1.metric("Ratings in view", f"{len(filtered):,}")
c2.metric("Movies in view", f"{filtered_movies['movie_id'].nunique():,}")
c3.metric("Mean rating in view", f"{filtered['rating'].mean():.2f}")

# --- Question 1 ---
n_rated_movies = filtered_movies["movie_id"].nunique()
genre_movies = explode_genres(filtered_movies)
genre_counts = (
    genre_movies.groupby("genre", as_index=False)["movie_id"]
    .nunique()
    .rename(columns={"movie_id": "movie_count"})
)
genre_counts["pct_of_movies"] = 100 * genre_counts["movie_count"] / n_rated_movies
genre_counts = genre_counts.sort_values("movie_count", ascending=True)

st.header("Question 1 — Genre breakdown")
st.subheader("What's the distribution of genres among the movies that were rated?")
st.markdown(
    f"""
**How multiple genres are handled, before any count:** each movie stores genres as a
pipe-separated string (`Comedy|Romance`). I split on `|` and explode so each tag is
its own row. I then keep **one row per movie** (`movie_id`) before counting, so this
is the mix of **{n_rated_movies:,} unique movies that appear in the ratings file**,
not 100,000 rating events.

*Toy Story* (`Animation|Children|Comedy`) adds **1** to Animation, **1** to Children,
and **1** to Comedy. It does not become a single combo category, and it is not counted
once per user who rated it.

Because tags overlap, the bars sum to **{int(genre_counts['movie_count'].sum()):,}**
movie–genre pairs (about **{genre_counts['movie_count'].sum() / n_rated_movies:.2f}**
genres per movie) — more than 100% of movies. That is expected. Two titles are tagged
`unknown` in the source file; they are kept as their own bar rather than dropped.
"""
)

fig1 = px.bar(
    genre_counts,
    x="movie_count",
    y="genre",
    orientation="h",
    title="Rated movies by genre (unique titles, sorted by count)",
    labels={"movie_count": "Number of unique movies", "genre": "Genre"},
    hover_data={"pct_of_movies": ":.1f"},
)
fig1.update_layout(**CHART_LAYOUT, height=560)
st.plotly_chart(fig1, use_container_width=True, key="q1_genre_counts")
st.caption(
    "Horizontal bar chart, sorted by count (not alphabetical). Not a pie: there are "
    "~19 categories and overlapping tags, so slices would not be a true partition of movies. "
    "Hover shows the share of unique rated movies that carry that genre."
)

# --- Question 2 ---
genre_avg = (
    explode_genres(filtered)
    .groupby("genre", as_index=False)
    .agg(
        avg_rating=("rating", "mean"),
        n_ratings=("rating", "size"),
        n_movies=("movie_id", "nunique"),
    )
    .sort_values("avg_rating", ascending=True)
)
highest_genre = genre_avg.iloc[-1]
lowest_genre = genre_avg.iloc[0]
named = genre_avg[genre_avg["genre"].str.lower() != "unknown"]
lowest_named = named.iloc[0]
genre_avg["highlight"] = "Other"
genre_avg.loc[genre_avg["genre"] == highest_genre["genre"], "highlight"] = "Highest"
genre_avg.loc[genre_avg["genre"] == lowest_genre["genre"], "highlight"] = "Lowest"

st.header("Question 2 — Genre satisfaction")
st.subheader("Which genres have the highest average rating? Which have the lowest?")
st.markdown(
    f"""
**Mean rating** = arithmetic mean of **user ratings** after the same `|` explode as
Question 1. A 5 on *Toy Story* counts toward Animation, Children, and Comedy. I do
**not** average per-movie first (that would equally weight a film with 2 ratings and
one with 300).

**Highest:** **{highest_genre['genre']}** at **{highest_genre['avg_rating']:.2f}**
({int(highest_genre['n_ratings']):,} ratings · {int(highest_genre['n_movies'])} movies).

**Lowest:** **{lowest_genre['genre']}** at **{lowest_genre['avg_rating']:.2f}**
({int(lowest_genre['n_ratings']):,} ratings · {int(lowest_genre['n_movies'])} movies).
Among named genres, **{lowest_named['genre']}** is lowest at
**{lowest_named['avg_rating']:.2f}**.

The 1–5 scale is compressed in practice (~{lowest_genre['avg_rating']:.2f}–{highest_genre['avg_rating']:.2f}),
so the axis is zoomed to the data instead of forced to 0–5.
"""
)

fig2 = px.bar(
    genre_avg,
    x="avg_rating",
    y="genre",
    orientation="h",
    color="highlight",
    color_discrete_map={
        "Highest": "#3DDC97",
        "Lowest": "#E50914",
        "Other": "#6E7681",
    },
    title="Mean user rating by genre (sorted)",
    labels={"avg_rating": "Mean rating (1–5)", "genre": "Genre", "highlight": ""},
    hover_data={"n_ratings": True, "n_movies": True, "avg_rating": ":.3f"},
)
fig2.update_layout(**CHART_LAYOUT, height=560, showlegend=False)
fig2.update_xaxes(range=[3.0, 4.1])
st.plotly_chart(fig2, use_container_width=True, key="q2_genre_means")
st.caption("Sorted by mean rating, not alphabetically. Green = highest, red = lowest.")

# --- Question 3 ---
by_year = (
    filtered.dropna(subset=["year"])
    .groupby("year", as_index=False)
    .agg(mean_rating=("rating", "mean"), n_ratings=("rating", "size"))
    .sort_values("year")
)
by_year_plot = by_year[by_year["n_ratings"] >= min_year_n]
overall = filtered["rating"].mean()

st.header("Question 3 — Ratings over time")
st.subheader("How has the mean rating changed across movie release years?")
st.markdown(
    f"""
This is **mean rating by movie release year** (`year`), not by when the user submitted
the rating (`rating_year` is mostly 1997–1998 in this file). Mean = average of all
rating rows for movies released that year.

Early decades have very few ratings (e.g. 1926 has 2). The sidebar **Hide sparse years**
control defaults to dropping years with fewer than **{min_year_n}** ratings so those
spikes don't look like a real trend. Overall mean in the current view:
**{overall:.2f}**.
"""
)

fig3 = px.line(
    by_year_plot,
    x="year",
    y="mean_rating",
    title="Mean rating by movie release year",
    labels={"year": "Release year", "mean_rating": "Mean rating (1–5)"},
    markers=True,
    hover_data={"n_ratings": True, "mean_rating": ":.3f"},
)
fig3.update_layout(**CHART_LAYOUT, height=420)
fig3.update_yaxes(range=[2.8, 4.3])
fig3.add_hline(
    y=overall,
    line_dash="dot",
    line_color="#8B949E",
    annotation_text="overall mean",
    annotation_position="top left",
)
st.plotly_chart(fig3, use_container_width=True, key="q3_mean_by_year")
st.caption(
    "Line chart over release year. Newer 1990s titles (the bulk of the catalog) sit "
    "slightly below the overall mean; older, still-rated classics sit above it."
)

# --- Question 4 ---
movie_stats = filtered.groupby(["movie_id", "title"], as_index=False).agg(
    avg_rating=("rating", "mean"),
    n_ratings=("rating", "size"),
)

genre_ids = None
if selected_genres:
    movie_genre_map = explode_genres(filtered_movies)[["movie_id", "genre"]]
    genre_ids = movie_genre_map[movie_genre_map["genre"].isin(selected_genres)][
        "movie_id"
    ].unique()

top50 = top_movies(movie_stats, 50, genre_ids)
top150 = top_movies(movie_stats, 150, genre_ids)
top_custom = top_movies(movie_stats, extra_floor, genre_ids)

st.header("Question 4 — Best movies, with a floor")
st.subheader(
    "What are the top 5 best-rated movies with at least 50 ratings? What changes at 150?"
)
st.markdown(
    """
**Floor** = a movie must have at least *n* ratings before its mean can appear in the
ranking. Without a floor, a 5.0 from two friends beats *Casablanca*. Rank is by mean
rating, with rating count as the tie-breaker.

Raising the floor from 50 → 150 drops Wallace & Gromit shorts that are loved but
less widely rated, and keeps widely seen classics.
"""
)

left, right = st.columns(2)
with left:
    fig50 = ranked_bar(top50, 50)
    if fig50 is None:
        st.warning("No movies meet a floor of 50 in the current filters.")
    else:
        st.plotly_chart(fig50, use_container_width=True, key="q4_floor_50")
        st.dataframe(
            top50.assign(avg_rating=lambda d: d["avg_rating"].round(3))[
                ["title", "avg_rating", "n_ratings"]
            ].rename(
                columns={
                    "title": "Movie",
                    "avg_rating": "Mean rating",
                    "n_ratings": "Ratings",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
with right:
    fig150 = ranked_bar(top150, 150)
    if fig150 is None:
        st.warning("No movies meet a floor of 150 in the current filters.")
    else:
        st.plotly_chart(fig150, use_container_width=True, key="q4_floor_150")
        st.dataframe(
            top150.assign(avg_rating=lambda d: d["avg_rating"].round(3))[
                ["title", "avg_rating", "n_ratings"]
            ].rename(
                columns={
                    "title": "Movie",
                    "avg_rating": "Mean rating",
                    "n_ratings": "Ratings",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

st.subheader(f"Custom floor: {extra_floor} ratings")
fig_c = ranked_bar(top_custom, extra_floor)
if fig_c is None:
    st.warning("No movies meet this custom floor in the current filters.")
else:
    st.plotly_chart(fig_c, use_container_width=True, key="q4_floor_custom")
    st.caption(
        "Use the sidebar slider to try floors other than 50 and 150. "
        "Optional genre filter applies to all three rankings."
    )

import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Steam Games DB",)

# Establishing a connection with the database
conn = st.connection(
    "games_dw",
    type="sql",
    url="mysql://Boznik:stadvdb@localhost:3306/games_dw"
)

def query_A(start_year, end_year):
    query = conn.query("""
    SELECT 
        dg.genre_name,
    CASE 
        WHEN dd.year IS NULL THEN 'grand_total'
        ELSE dd.year 
    END AS year,
        COUNT(fg.game_id) AS sub_total
    FROM fact_games fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
        INNER JOIN dim_date dd ON fg.date_id = dd.year 
    WHERE 
        dd.year BETWEEN """ + str(start_year) + """ AND """ + str(end_year) + """
    GROUP BY dg.genre_name, dd.year WITH ROLLUP
    ORDER BY 
        dg.genre_name,
        dd.year;""")
    return pd.DataFrame(query)

def query_B(start_year, end_year, genre):
    query = conn.query(f"""
    SELECT 
        p.platform_name,
        COUNT(fg.game_id) AS platform_distribution
    FROM fact_games fg
        JOIN dim_date dd ON fg.date_id = dd.year
        JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        JOIN dim_genre g ON ggb.genre_id = g.genre_id
        JOIN game_platform_bridge gpb ON fg.game_id = gpb.game_id
        JOIN dim_platform p ON gpb.platform_id = p.platform_id
    WHERE 
        dd.year BETWEEN {start_year}  AND {end_year} AND
        g.genre_name = '{genre}'
    GROUP BY g.genre_name, p.platform_name
    ORDER BY g.genre_name,platform_distribution DESC;""")
    return pd.DataFrame(query)

def query_C():
    query = conn.query("""
    SELECT
        dg.genre_name AS Genre,
        ROUND(AVG(fg.price), 2) AS Average_Price
    FROM
        fact_games fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
    GROUP BY
        dg.genre_name
    ORDER BY
        dg.genre_name;
    """)
    return pd.DataFrame(query)

def query_D():
    query = conn.query("""
            SELECT
            dp.platform_name AS Platform,
            dg.genre_name AS Genre,
            dd.year AS Year,
            SUM(fg.total_positive_reviews + fg.total_negative_reviews) AS Total_Reviews
        FROM
            fact_games fg
            INNER JOIN game_platform_bridge gpb ON fg.game_id = gpb.game_id
            INNER JOIN dim_platform dp ON gpb.platform_id = dp.platform_id
            INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
            INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
            INNER JOIN dim_date dd ON fg.date_id = dd.date_id
        GROUP BY
            dp.platform_name,
            dg.genre_name,
            dd.year
        ORDER BY
            dp.platform_name, dg.genre_name, dd.year;""")
    return pd.DataFrame(query)

def query_D1():
    query = conn.query("""
    SELECT
        dg.genre_name AS Genre,
        CONCAT(FORMAT(SUM(fg.total_positive_reviews), 0), ':', FORMAT(SUM(fg.total_negative_reviews), 0)) AS Positive_Negative_Ratio
    FROM
        fact_games fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
    GROUP BY
        dg.genre_name
    ORDER BY
        dg.genre_name;""")
    return pd.DataFrame(query)

def query_D2():
    query = conn.query("""
    SELECT
        fg.game_id as Game_ID,
        dg.genre_name AS Genre,
        dp.platform_name AS Platform,
        dd.year AS Year,
        fg.total_positive_reviews AS Positive_Reviews,
        fg.total_negative_reviews AS Negative_Reviews,
        ROUND((fg.total_positive_reviews * 100.0) / NULLIF((fg.total_positive_reviews + fg.total_negative_reviews), 0), 2) AS Positive_Review_Percentage
    FROM
        fact_games fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
        INNER JOIN game_platform_bridge gpb ON fg.game_id = gpb.game_id
        INNER JOIN dim_platform dp ON gpb.platform_id = dp.platform_id
        INNER JOIN dim_date dd ON fg.date_id = dd.date_id
    WHERE
        ROUND((fg.total_positive_reviews * 100.0) / NULLIF((fg.total_positive_reviews + fg.total_negative_reviews), 0), 2) > 75
    ORDER BY
        dg.genre_name, dp.platform_name, dd.year;""")
    return pd.DataFrame(query)

def generate_report_A(start_year, end_year):
    data = query_A(start_year, end_year) # fetches data from query

    # pivots table to better visualize the results
    pivot_data = data.pivot_table(
        index='genre_name',
        columns='year',
        values='sub_total',
        fill_value=0
    )

    # renaming column
    pivot_data = pivot_data.rename(columns={
        'grand_total': 'Total',
    })

    # rename axis
    pivot_data = pivot_data.rename_axis('Genre').reset_index()
    return pivot_data # returns streamlit dataframe

def generate_report_B(start_year, end_year, genre):
    data = query_B(start_year, end_year, genre)

    return data

def generate_report_C():
    data = query_C()
    chart = alt.Chart(data).mark_bar().encode(
        x=alt.X('Genre', axis=alt.Axis(title='Movie Genre')),
        y=alt.Y('Average_Price', axis=alt.Axis(title='Average Price ($)'),
                scale=alt.Scale(domain=[0, data['Average_Price'].max()])),
        size='Average_Price'
    ).properties(width=500).interactive()

    return chart #returns altair bar chart

def generate_report_D():
    test_df = query_D()
    chart = alt.Chart(test_df).mark_line().encode(
        x='Year:O',
        y='Total_Reviews:Q',
        color='Genre:N',
        facet='Platform:N'
    ).properties(width=500).interactive()

    return chart # returns altair line chart

def generate_report_D1():
    df = query_D1()
    df['Positive_Reviews'] = df['Positive_Negative_Ratio'].apply(lambda x: int(x.split(':')[0].replace(',', '')))
    df['Negative_Reviews'] = df['Positive_Negative_Ratio'].apply(lambda x: int(x.split(':')[1].replace(',', '')))
    chart = alt.Chart(df).transform_fold(
        ['Positive_Reviews', 'Negative_Reviews'],  # Columns to fold
        as_=['Review_Type', 'Count']  # New column names
    ).mark_bar().encode(
        x=alt.X('Genre:N', title='Genre'),
        y=alt.Y('Count:Q', title='Number of Reviews'),
        color='Review_Type:N',
        xOffset='Review_Type:N'
    ).properties(width=500).interactive()

    return chart # returns altair bar chart

def generate_report_D2():
    df = query_D2()
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X('Year:O', title='Year'),
        y=alt.Y('Positive_Review_Percentage:Q', title='Positive Review %'),
        color='Genre:N',
        facet='Platform:N'
    ).properties(width=500).interactive()

    return chart # returns altair line chart

def main():
    st.title("Steam Games DB")

    with st.sidebar:
        st.title("Navigation bar")

        option = st.selectbox(
            "Select report to generate",
            ("Report A", "Report B", "Report C", "Report D", "Report D1", "Report D2"),
            index=None,
            placeholder="Select report...",
        )

    # Initialize session states
    if 'start_yearA' not in st.session_state:
        st.session_state.start_yearA = 1997
    if 'end_yearA' not in st.session_state:
        st.session_state.end_yearA = 2025
    if 'start_yearB' not in st.session_state:
        st.session_state.start_yearB = 1997
    if 'end_yearB' not in st.session_state:
        st.session_state.end_yearB = 2025
    if 'genreB' not in st.session_state:
        st.session_state.genreB = 'action'

    if option == "Report A":
        st.write("No. of Games Released within a range of Two Different Years by Genre")

        with st.form(key='year_selection_formA'):
            # Use session state values for the select_slider
            start_year, end_year = st.select_slider(
                "Select a range between two different years",
                options=list(range(1997, 2026)),
                value=(st.session_state.start_yearA, st.session_state.end_yearA)
            )
            submit = st.form_submit_button(label="Run Query")

            if submit:
                # Store the selected years in session state
                st.session_state.start_yearA = start_year
                st.session_state.end_yearA = end_year

                # Form validation
                if start_year == end_year:
                    st.toast("Warning: Start year cannot be equal to end year.")
                elif end_year < start_year:
                    st.toast("Warning: End year cannot be less than start year.")
                else:
                    st.toast("Generating Report...")
                    chart = generate_report_A(start_year, end_year)
                    st.dataframe(chart)

    if option == "Report B":
        st.write("Platform Distribution of each genre released in the within X to X years")

        with st.form(key='year_selection_formB'):
            # Use session state values for the select_slider
            start_year, end_year = st.select_slider(
                "Select a range between two different years",
                options=list(range(1997, 2026)),
                value=(st.session_state.start_yearB, st.session_state.end_yearB)
            )

            option = st.selectbox(
                "Select Genre",
                options = ["360 video", "accounting", "action",
                           "adventure", "animation & modeling",
                           "audio production", "casual", "design & illustration",
                           "documentary", "early access", "education", "episodic",
                           "free to play", "game development", "gore", "indie",
                           "massively multiplayer", "movie", "nudity", "photo editing",
                           "racing", "rpg", "sexual content", "short", "simulation",
                           "software training", "sports", "strategy", "tutorial", "utilities",
                           "video production", "violent", "web publishing"]
,
                index=None,
                placeholder="Select Genre...",
            )

            submit = st.form_submit_button(label="Run Query")

            if submit:
                # Store the selected years in session state
                st.session_state.start_yearB = start_year
                st.session_state.end_yearB = end_year
                st.session_state.genreB = option

                # Form validation
                if start_year == end_year:
                    st.toast("Warning: Start year cannot be equal to end year.")
                elif end_year < start_year:
                    st.toast("Warning: End year cannot be less than start year.")
                else:
                    st.toast("Generating Report...")
                    chart = generate_report_B(start_year, end_year, option)
                    st.dataframe(chart)

    if option == "Report C":
        chartC = generate_report_C()
        st.altair_chart(chartC)

    if option == "Report D":
        chartD = generate_report_D()
        st.altair_chart(chartD)

    if option == "Report D1":
        chartD1 = generate_report_D1()
        st.altair_chart(chartD1)

    if option == "Report D2":
        chartD2 = generate_report_D2()
        st.altair_chart(chartD2)

    if option == "":
        st.write("# Select a report to generate in the sidebar.")

if __name__ == "__main__":
  main()


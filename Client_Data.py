import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timezone
import plotly.express as px

# ✅ Streamlit App Title
st.title("📊 ClickUp Time Tracking Dashboard")

# ✅ API Credentials
API_KEY = "pk_81690258_EEBF5NEHT52AI072L0VTMQ86I83EBW1J"
TEAM_ID = 7272257

# ✅ Assignee List
ASSIGNEES = "49211404,56674259,81808051,81800109,81747238,7342900,44580634,81655103,38510068,81690166,81763398,44486518,81690258,38505282,7340203,7340200,56674259,74563475,49206133,7340189,44566763,49207486,48603820,81701168,7340198,81717875,44681618,38574793,81710890,81806818,49204813,81681139,49206121,56668217,49356475,81708648,81690258,1748400462,7340197,81690258,56674259,44681618,87739130,164439229,81878404,87761556,38614499,158484434,74563475,87750571,49205703,87692096,164620704,55330910,87646559"

# ✅ Specific Client Tags to Include
SPECIFIC_TAGS = {"kamoa", "platreef", "kico", "oksut", "pmc", "metalkol", "swakop", "witnessing", "ivm", "gold vale",
                 "demo site"}

# ✅ Streamlit Sidebar for Date Selection
st.sidebar.header("📅 Select Date Range")
start_date = st.sidebar.date_input("Start Date", datetime(2025, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime(2025, 1, 31))

# ✅ Convert selected dates to Unix timestamps (milliseconds)
START_DATE = int(datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000)
END_DATE = int(datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc).timestamp() * 1000)


# ✅ Function to Fetch Data (No Caching)
def fetch_clickup_data(start_date, end_date):
    url = f"https://api.clickup.com/api/v2/team/{TEAM_ID}/time_entries?start_date={start_date}&end_date={end_date}&assignee={ASSIGNEES}"

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        st.error(f"❌ API Error: {response.json()}")
        return []


# ✅ Add Refresh Button
if st.sidebar.button("🔄 Refresh Data"):
    st.session_state["data"] = fetch_clickup_data(START_DATE, END_DATE)  # Force re-fetch

# ✅ Load Data (Check if it exists in session state)
if "data" not in st.session_state:
    st.session_state["data"] = fetch_clickup_data(START_DATE, END_DATE)

data = st.session_state["data"]  # Use session-stored data

# ✅ Convert JSON Data to DataFrame
if data:
    df = pd.DataFrame(data)

    # ✅ Ensure 'start' and 'end' columns are numeric
    df["Start (Unix)"] = pd.to_numeric(df["start"], errors="coerce")
    df["End (Unix)"] = pd.to_numeric(df["end"], errors="coerce")

    # ✅ Convert Unix timestamps to DateTime
    df["StartDate"] = df["Start (Unix)"].apply(
        lambda x: datetime.fromtimestamp(x / 1000, timezone.utc) if pd.notna(x) else None)
    df["EndDate"] = df["End (Unix)"].apply(
        lambda x: datetime.fromtimestamp(x / 1000, timezone.utc) if pd.notna(x) else None)

    # ✅ Extract Nested Fields (Task, User, Tags)
    df["TaskID"] = df["task"].apply(lambda x: x["id"] if isinstance(x, dict) else None)
    df["UserName"] = df["user"].apply(lambda x: x["username"] if isinstance(x, dict) else None)

    # ✅ Extract Tag Names (convert to lowercase for comparison)
    df["TagName"] = df["tags"].apply(
        lambda tags: [tag["name"].lower() for tag in tags] if isinstance(tags, list) else [])

    # ✅ Convert Duration (ms) to Hours
    df["Duration (ms)"] = pd.to_numeric(df["duration"], errors="coerce")
    df["Duration (hours)"] = df["Duration (ms)"] / (1000 * 60 * 60)

    # ✅ Extract Billable Status
    df["Billable"] = df["billable"].apply(lambda x: "Billable" if x else "Non-Billable")

    # ✅ Explode Tags (Create a row for each tag)
    df = df.explode("TagName")

    # ✅ **Filter Only the Specific Tags**
    df = df[df["TagName"].isin(SPECIFIC_TAGS)]

    # ✅ Sidebar Dropdown for Selecting User (Includes "All Users" Option)
    user_options = ["All Users"] + df["UserName"].unique().tolist()
    selected_user = st.sidebar.selectbox("👤 Select User", options=user_options)

    # ✅ Filter Data for Selected User
    if selected_user != "All Users":
        user_df = df[df["UserName"] == selected_user]
    else:
        user_df = df

    # ✅ Summary Table Calculation
    summary_df = user_df.groupby(["TagName", "Billable"])["Duration (hours)"].sum().unstack(fill_value=0)
    summary_df["Total Hours"] = summary_df.sum(axis=1)
    summary_df["% Billable"] = (summary_df.get("Billable", 0) / summary_df["Total Hours"]) * 100
    summary_df = summary_df.reset_index().rename(
        columns={"TagName": "Client Tag", "Non-Billable": "Non Billable", "Billable": "Billable",
                 "Total Hours": "Total Hours", "% Billable": "Percentage Billable"})

    # ✅ Display Summary Table at the Top
    st.write("### 🏆 Time Tracking Summary")
    st.dataframe(summary_df, hide_index=True)

    # ✅ Pie Chart - Individual User OR All Users
    if selected_user != "All Users":
        fig_pie = px.pie(user_df, names="TagName", values="Duration (hours)",
                         title=f"Time Breakdown for {selected_user}")
        st.plotly_chart(fig_pie)
    else:
        st.write("### 🌍 Combined Time Distribution")
        fig_combined = px.pie(df, names="TagName", values="Duration (hours)",
                              title="Time Distribution Across All Users")
        st.plotly_chart(fig_combined)

        # ✅ NEW: Pie Chart for Total Hours Logged Per User
        st.write("### 🔥 Work Distribution Across Users Specific To Tags")
        user_hours_df = df.groupby("UserName")["Duration (hours)"].sum().reset_index()
        fig_user_pie = px.pie(user_hours_df, names="UserName", values="Duration (hours)",
                              title="Total Hours Logged Per User")
        st.plotly_chart(fig_user_pie)

    # ✅ Stacked Bar Chart - Updated for Selected User
    st.write("### 📊 Stacked Bar Chart - Hours per Activity")
    stacked_chart = user_df.groupby(["TagName", "Billable"])["Duration (hours)"].sum().reset_index()
    fig_stacked = px.bar(
        stacked_chart,
        x="TagName",
        y="Duration (hours)",
        color="Billable",
        title=f"Hours Logged per Activity (Billable vs Non-Billable) - {selected_user}",
        barmode="stack"
    )
    st.plotly_chart(fig_stacked)

else:
    st.warning("⚠️ No time tracking data available for the selected period.")


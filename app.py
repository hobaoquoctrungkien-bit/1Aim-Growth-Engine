import streamlit as st

from database import (
    create_inquiry,
    get_open_tasks,
    get_task_counts_by_type,
    init_db,
)

st.set_page_config(
    page_title="1Aim Growth Engine",
    layout="wide"
)

init_db()

st.title("🚀 1Aim Growth Engine")

task_counts = get_task_counts_by_type()
open_tasks = get_open_tasks()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Quote Follow-up",
        task_counts.get("quote_follow_up", 0)
    )

with col2:
    st.metric(
        "Lead Nurturing",
        task_counts.get("relationship_touch", 0)
    )

with col3:
    st.metric(
        "New Lead Outreach",
        task_counts.get("new_lead_outreach", 0)
    )

with col4:
    st.metric(
        "Prepare Quote",
        task_counts.get("prepare_quote", 0)
    )

st.divider()

st.subheader("Today Cockpit")

cockpit_col1, cockpit_col2, cockpit_col3 = st.columns(3)


def show_tasks(task_type):
    tasks = [
        task for task in open_tasks
        if task["task_type"] == task_type
    ]

    if not tasks:
        st.info("No open tasks.")
        return

    for task in tasks:
        st.write(task["title"])

        if task["due_date"]:
            st.caption(f"Due: {task['due_date']}")


with cockpit_col1:
    st.markdown("**Quote Follow-up**")
    show_tasks("quote_follow_up")

with cockpit_col2:
    st.markdown("**Lead Nurturing**")
    show_tasks("relationship_touch")

with cockpit_col3:
    st.markdown("**New Lead Outreach**")
    show_tasks("new_lead_outreach")

st.divider()

st.subheader("Today's Actions")
show_tasks("prepare_quote")

st.divider()

st.subheader("New Inquiry")

inquiry_text = st.text_area(
    "Paste inquiry here",
    height=200
)

if st.button("Save Inquiry"):
    if inquiry_text.strip():
        create_inquiry(inquiry_text)
        st.success("Inquiry saved successfully.")
        st.rerun()
    else:
        st.warning("Paste an inquiry before saving.")

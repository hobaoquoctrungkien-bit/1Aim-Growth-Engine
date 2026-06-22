from html import escape


STATUS_BADGE_COLORS = {
    "red": ("#451f25", "#ff5a5f", "#ffd6d9"),
    "green": ("#173322", "#2ecc71", "#d6ffe4"),
    "yellow": ("#3a3414", "#ffcc00", "#fff2b8"),
    "blue": ("#142b44", "#2f80ed", "#d9eaff"),
    "neutral": ("#1c2636", "#3d4b63", "#edf2f7"),
}


def status_badge_html(label, tone="neutral"):
    background, border, text_color = STATUS_BADGE_COLORS.get(
        tone,
        STATUS_BADGE_COLORS["neutral"],
    )
    safe_label = escape(str(label))

    return f"""
        <span class="ui-status-badge" style="
            border-color:{border};
            background:{background};
            color:{text_color};
        ">{safe_label}</span>
    """

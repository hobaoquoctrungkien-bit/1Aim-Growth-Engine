FONT_SIZE_XS = 16
FONT_SIZE_SM = 18
FONT_SIZE_MD = 20
FONT_SIZE_LG = 22
FONT_SIZE_XL = 28
FONT_SIZE_XXL = 40

UI_SCALE_OPTIONS = ["Normal", "Large", "Extra Large"]
DEFAULT_UI_SCALE = "Large"

UI_SCALE_MULTIPLIERS = {
    "Normal": 1.0,
    "Large": 1.15,
    "Extra Large": 1.3,
}


def get_typography_tokens(ui_scale=DEFAULT_UI_SCALE):
    # Accessibility: use global typography tokens only.
    multiplier = UI_SCALE_MULTIPLIERS.get(ui_scale, UI_SCALE_MULTIPLIERS[DEFAULT_UI_SCALE])

    return {
        "xs": round(FONT_SIZE_XS * multiplier),
        "sm": round(FONT_SIZE_SM * multiplier),
        "md": round(FONT_SIZE_MD * multiplier),
        "lg": round(FONT_SIZE_LG * multiplier),
        "xl": round(FONT_SIZE_XL * multiplier),
        "xxl": round(FONT_SIZE_XXL * multiplier),
    }

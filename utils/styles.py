# For any styles which need to be stored "pythonically"
# e.g. styles for dash_table

DATATABLE_STYLES = {
    "style_header": {
        "textAlign": "center",
        "backgroundColor": "black",
        "color": "white",
        "text-transform": "uppercase",
    },
    "style_cell": {
        "textAlign": "center",
        "minWidth": "25%",
        "width": "25%",
        "maxWidth": "25%",
    },
    "style_data_conditional": [
        {
            "if": {"state": "active"},
            "backgroundColor": "white",
            "border": "1px solid #999999",
            "textAlign": "center",
        }
    ],
    "style_table": {"maxHeight": "60vh", "overflowY": "auto"},
    "fixed_rows": {"headers": True},
}

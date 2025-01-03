import os
import redis
import json
import dash_bootstrap_components as dbc
import dash_ag_grid as dag

from dash import (
    Dash,
    html,
    dcc,
    Input,
    Output,
    State,
    callback,
    no_update,
    clientside_callback,
    set_props,
)

from utils.helpers import (
    random_workout_id,
    create_workout_plan,
    find_next_exercise,
    formulate_workout_duration,
)

from utils.constants import START_COUNTDOWN, DEFAUlT_DURATION

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

redis_instance = redis.StrictRedis.from_url(
    os.environ.get("REDIS_URL", "redis://127.0.0.1:6379")
)

app.layout = [
    html.Div(
        [
            html.H1("Workout Intervals", id="app-title"),
            dbc.Input(id="workout-name", value=random_workout_id()),
            dag.AgGrid(
                id="workout-editor",
                columnDefs=[
                    {
                        "headerName": "INTERVAL",
                        "field": "interval",
                        "editable": False,
                        "rowDrag": True,
                        "suppressMovable": True,
                        "resizable": False,
                        "sortable": False,
                    },
                    {
                        "headerName": "EXERCISE",
                        "field": "exercise",
                        "editable": True,
                        "suppressMovable": True,
                        "resizable": False,
                        "sortable": False,
                    },
                    {
                        "headerName": "DURATION (S)",
                        "field": "duration",
                        "editable": True,
                        "type": "numericColumn",
                        "suppressMovable": True,
                        "resizable": False,
                        "sortable": False,
                    },
                    {
                        "headerName": "SUB-INTERVALS",
                        "field": "sub-intervals",
                        "editable": True,
                        "type": "numericColumn",
                        "suppressMovable": True,
                        "resizable": False,
                        "sortable": False,
                    },
                ],
                rowData=[],
                dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True},
                columnSize="sizeToFit",
            ),
            html.Div(id="workout-duration"),
            html.Div(
                id="edit-page-buttons-div",
                children=[
                    html.Div(
                        [
                            dbc.Button(
                                "Add Interval",
                                id="add-interval",
                                n_clicks=0,
                                class_name="button-style",
                            ),
                            dbc.Button(
                                "Delete Interval",
                                id="delete-interval",
                                n_clicks=0,
                                class_name="button-style",
                            ),
                        ]
                    ),
                    dbc.Button(
                        "Launch Workout",
                        id="launch-workout",
                        n_clicks=0,
                        class_name="button-style",
                    ),
                    html.Div(
                        [
                            dbc.Button(
                                "Save Workout",
                                id="save-workout",
                                n_clicks=0,
                                class_name="button-style",
                            ),
                            dbc.Button(
                                "Load Workout",
                                id="load-workout",
                                n_clicks=0,
                                class_name="button-style",
                            ),
                        ]
                    ),
                ],
            ),
            html.Div(
                id="edit-page-alerts-div",
                children=[
                    dbc.Alert(
                        id="workout-launch-alert",
                        color="danger",
                        dismissable=True,
                        is_open=False,
                    ),
                    dbc.Alert(id="save-workout-alert", is_open=False, dismissable=True),
                    dbc.Alert(
                        "No saved workouts!",
                        id="load-workout-alert",
                        is_open=False,
                        color="danger",
                        dismissable=True,
                    ),
                ],
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Saved Workouts"), class_name="modal-header"
                    ),
                    dbc.ModalBody(
                        [
                            dcc.Dropdown(
                                id="saved-workouts",
                                placeholder="Select a saved workout",
                            ),
                            html.Div(
                                id="select-workout-div",
                                children=[
                                    dbc.Button(
                                        "Select Workout",
                                        id="select-workout",
                                        class_name="button-style",
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
                id="load-workout-modal",
                size="sm",
            ),
            html.Div(
                id="invisible-elements",
                children=[
                    dcc.Store(
                        id="workout-plan",
                    ),
                    html.Audio(
                        id="audio-player",
                        controls=False,
                        src="/assets/bell.mp3",
                    ),
                    dcc.Store(id="trigger-audio", data="bell"),
                    html.Div(id="dummy-div", style={"display": "none"}),
                ],
            ),
            dbc.Modal(
                [
                    dbc.ModalBody(
                        [
                            html.Div(id="total-countdown"),
                            html.Div(
                                id="countdown",
                                children=START_COUNTDOWN,
                            ),
                            html.Div(
                                id="workout-content",
                                children="Workout not started",
                            ),
                            html.Div(id="next-exercise"),
                            dcc.Interval(
                                id="workout-timer",
                                interval=1000,
                                max_intervals=-1,
                                disabled=True,
                                n_intervals=0,
                            ),
                            html.Div(
                                id="bottom-display",
                                children=[
                                    dbc.Progress(id="progress-bar", label="", value=0),
                                    html.Div(
                                        id="workout-mode-buttons",
                                        children=[
                                            dbc.Button(
                                                "Start Workout",
                                                id="start-workout",
                                                n_clicks=0,
                                                class_name="button-style",
                                            ),
                                            dbc.Button(
                                                "Pause Workout",
                                                id="pause-workout",
                                                n_clicks=0,
                                                disabled=True,
                                                class_name="button-style",
                                            ),
                                            dbc.Button(
                                                "Close Workout",
                                                id="close-workout",
                                                n_clicks=0,
                                                class_name="button-style",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                        id="workout-modal-body",
                    ),
                ],
                id="workout-modal",
                is_open=False,
                fullscreen=True,
                keyboard=False,
                backdrop="static",
            ),
        ]
    )
]


@callback(Input("workout-editor", "virtualRowData"), State("workout-editor", "rowData"))
def maintain_interval_order(virtual_data, row_data):
    if len(virtual_data) != len(row_data):
        return  # row was added or deleted - this is handled in another callback
    if not len(virtual_data):
        set_props(
            "workout-duration",
            {"children": formulate_workout_duration(0, prepend_label=True)},
        )
    # Update interval numbers based on row data and
    # update total workout duration
    i = 1
    duration = 0
    for row in virtual_data:
        row["interval"] = i
        duration += row["duration"]
        i += 1
    set_props("workout-editor", {"rowData": virtual_data})
    set_props(
        "workout-duration",
        {"children": formulate_workout_duration(duration, prepend_label=True)},
    )


@callback(Input("add-interval", "n_clicks"), State("workout-editor", "rowData"))
def add_interval(add, current):
    if add:
        next_interval = len(current) + 1
        current.append(
            {
                "interval": next_interval,
                "exercise": "Exercise {}".format(next_interval),
                "duration": DEFAUlT_DURATION,
                "sub-intervals": 1,
            }
        )
        set_props("workout-editor", {"rowData": current})


@callback(Input("delete-interval", "n_clicks"))
def delete_intervals(delete):
    if delete:
        set_props("workout-editor", {"deleteSelectedRows": True})


# TODO: test this callback
@callback(Input("select-workout", "n_clicks"), State("saved-workouts", "value"))
def select_workout(select, saved_workout_name):
    if select:
        saved_workout_data = json.loads(
            redis_instance.hget("saved_workouts", saved_workout_name.encode("utf-8"))
        )
        set_props("workout-editor", {"rowData": saved_workout_data})
        set_props("workout-name", {"value": saved_workout_name.replace("_", " ")})
        set_props("load-workout-modal", {"is_open": False})


# TODO: test this
@callback(Input("load-workout", "n_clicks"))
def load_saved_workouts(load):
    if load:
        try:
            saved_workouts = [
                w.decode("utf-8") for w in redis_instance.hkeys("saved_workouts")
            ]  # Decode saved names to string format
        except:
            saved_workouts = []
        if not len(saved_workouts):  # no workouts saved
            set_props("load-workout-alert", {"is_open": True})
        else:
            saved_workouts = [
                {"label": w.replace("_", " "), "value": w} for w in saved_workouts
            ]
            set_props("load-workout-modal", {"is_open": True})
            set_props("saved-workouts", {"options": saved_workouts})


@callback(
    Input("save-workout", "n_clicks"),
    State("workout-name", "value"),
    State("workout-editor", "rowData"),
)
def save_workout(save, workout_name, workout_data):
    if not save:
        return
    if not len(workout_data):
        set_props("save-workout-alert", {"children": "Workout is empty!"})
        set_props("save-workout-alert", {"is_open": True})
        set_props("save-workout-alert", {"color": "danger"})
        return  # TODO: make sure this works
    if not workout_name:
        workout_name = "Workout #{}".format(random_workout_id)
    workout_id = workout_name.replace(
        " ", "_"
    )  # remove spaces from name to create workout_id
    try:
        # Display success message if data is successfully set in redis
        redis_instance.hset("saved_workouts", workout_id, json.dumps(workout_data))
        set_props(
            "save-workout-alert",
            {"children": f"'{workout_name}' successfully saved!"},
        )
        set_props("save-workout-alert", {"is_open": True})
        set_props("save-workout-alert", {"color": "success"})
    except:
        set_props(
            "save-workout-alert",
            {
                "children": "Cannot save workout because redis connection cannot be established"
            },
        )
        set_props("save-workout-alert", {"is_open": True})
        set_props("save-workout-alert", {"color": "danger"})


@callback(Output("select-workout", "disabled"), Input("saved-workouts", "value"))
def allow_saved_workout_selection(selection):

    return False if selection else True


@callback(Input("launch-workout", "n_clicks"), State("workout-editor", "rowData"))
def launch_workout(launch, workout_data):
    if not launch:
        return

    # Handling the case where workout is empty
    if not len(workout_data):
        set_props(
            "workout-launch-alert", {"children": "Please add at least 1 interval"}
        )
        set_props("workout-launch-alert", {"is_open": True})
        return
    # Converts tabular workout data to data to be stored in "workout-plan"
    # Start first exercise after START_COUNTDOWN seconds
    plan = create_workout_plan(workout_data, timestamp=START_COUNTDOWN)
    if type(plan) == str:
        set_props("workout-launch-alert", {"children": plan})
        set_props("workout-launch-alert", {"is_open": True})
    else:
        set_props("workout-plan", {"data": plan})
        set_props("workout-modal", {"is_open": True})


@callback(
    Input("start-workout", "n_clicks"),
    State("workout-timer", "disabled"),
    State("workout-plan", "data"),
)
def start_workout(start, timer_disabled, workout_plan):
    if start and not timer_disabled:
        return
    if start:
        first_exercise = (
            "Up next: "
            + workout_plan[str(workout_plan["timestamp_list"][0])]["exercise"]
        )
        set_props("workout-timer", {"disabled": False})
        set_props("workout-content", {"children": "Starting workout"})
        set_props("trigger-audio", {"data": "bell"})
        set_props("workout-timer", {"n_intervals": 0})
        set_props("pause-workout", {"disabled": False})
        set_props("next-exercise", {"children": first_exercise})


@callback(Input("close-workout", "n_clicks"))
def close_workout(close):
    if close:
        set_props("workout-timer", {"disabled": True})
        set_props("workout-content", {"children": "Workout not started"})
        set_props("pause-workout", {"children": "Pause Workout"})
        set_props("workout-timer", {"n_intervals": 0})
        set_props("pause-workout", {"disabled": True})
        set_props("next-exercise", {"children": ""})
        set_props("workout-plan", {"data": []})  # TODO: is this necessary?
        set_props("workout-modal", {"is_open": False})
        set_props("total-countdown", {"children": ""})


@callback(Input("pause-workout", "n_clicks"), State("workout-timer", "disabled"))
def pause_workout(pause, timer_disabled):
    if pause and timer_disabled:
        set_props("workout-timer", {"disabled": False})
        set_props("pause-workout", {"children": "Pause Workout"})
    elif pause:
        set_props("workout-timer", {"disabled": True})
        set_props("pause-workout", {"children": "Resume Workout"})


@callback(
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
    State("workout-timer", "disabled"),
)
def operate_workout(n_intervals, workout_plan, timer_disabled):
    if timer_disabled:
        return
    if n_intervals in workout_plan["timestamp_list"]:
        timestamp_str = str(n_intervals)
        current_exercise = workout_plan[timestamp_str]["exercise"]
        if (
            not current_exercise
        ):  # the current exercise is not changing, just trigger the audio
            set_props("trigger-audio", {"data": workout_plan[timestamp_str]["audio"]})
            return
        elif current_exercise == "Finished":
            set_props("workout-timer", {"disabled": True})
            set_props("next-exercise", {"children": ""})
            set_props("pause-workout", {"disabled": True})
        else:
            next_exercise = find_next_exercise(
                workout_plan, n_intervals, current_exercise
            )
            set_props("next-exercise", {"children": next_exercise})

        set_props("workout-content", {"children": current_exercise})
        set_props("trigger-audio", {"data": workout_plan[timestamp_str]["audio"]})


@callback(
    Output("progress-bar", "value"),
    Output("progress-bar", "label"),
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
    prevent_intial_call=True,
)
def progress_bar(n_intervals, workout_plan):
    if not n_intervals:
        return 0, "0% complete"
    else:
        total_duration = workout_plan["total_duration"]
        progress = int((n_intervals / total_duration) * 100)
        return progress, "{}%".format(progress)


@callback(
    Output("total-countdown", "children"),
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
)
def total_countdown(n_intervals, workout_plan):
    if not workout_plan or "total_duration" not in workout_plan.keys():
        return
    total_length = workout_plan["total_duration"]
    return formulate_workout_duration(total_length - n_intervals)


@callback(
    Output("countdown", "children"),
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
    State("countdown", "children"),
    prevent_initial_call=True,
)
def count_down(n_intervals, workout_plan, current_count):
    # If workout has not started
    if int(n_intervals) == 0:
        return START_COUNTDOWN

    # When new interval begins, update the countdown
    if (
        n_intervals in workout_plan["timestamp_list"]
        and workout_plan[str(n_intervals)]["countdown"]  # countdown is non-zero
    ):
        return workout_plan[str(n_intervals)]["countdown"]

    # Stop counting when countdown reaches zero
    elif current_count == 0:
        return no_update

    # Decrease the countdown by 1 if no interval change
    else:
        return current_count - 1


@callback(
    Output("audio-player", "src"),
    Input("trigger-audio", "data"),
)
def change_audio(audio):
    return "/assets/{}.mp3".format(audio)


clientside_callback(
    """
    function(n){
        const audioElement = document.querySelector('#audio-player')
        audioElement.autoplay=true;
        audioElement.load();
        return ''
    }
    """,
    Output("dummy-div", "children"),
    Input("trigger-audio", "data"),
    prevent_initial_call=True,
)


if __name__ == "__main__":
    app.run(debug=True)

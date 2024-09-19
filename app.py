import os
import redis
import json
import dash_bootstrap_components as dbc

from dash import (
    Dash,
    html,
    dash_table,
    dcc,
    Input,
    Output,
    State,
    callback,
    ctx,
    no_update,
    clientside_callback,
)

from utils.helpers import (
    random_workout_id,
    create_workout_plan,
    find_next_exercise,
)
from utils.styles import DATATABLE_STYLES
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
            dash_table.DataTable(
                id="workout-editor",
                columns=[
                    {"name": "Interval", "id": "interval", "editable": False},
                    {"name": "Exercise", "id": "exercise"},
                    {"name": "Duration(s)", "id": "duration", "type": "numeric"},
                    {"name": "Sub-Intervals", "id": "sub-intervals", "type": "numeric"},
                ],
                data=[],
                editable=True,
                row_deletable=True,
                style_header=DATATABLE_STYLES["style_header"],
                style_cell=DATATABLE_STYLES["style_cell"],
                style_data_conditional=DATATABLE_STYLES["style_data_conditional"],
                style_table=DATATABLE_STYLES["style_table"],
                fixed_rows=DATATABLE_STYLES["fixed_rows"],
            ),
            html.Div(
                id="edit-page-buttons-div",
                children=[
                    dbc.Button(
                        "Add Interval",
                        id="add-interval",
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
                    dbc.Button(
                        "Launch Workout",
                        id="launch-workout",
                        n_clicks=0,
                        class_name="button-style",
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


@callback(
    Output("workout-editor", "data"),
    Output("workout-name", "value"),
    Input("add-interval", "n_clicks"),
    Input("workout-editor", "data_previous"),
    Input("select-workout", "n_clicks"),
    State("workout-editor", "data"),
    State("saved-workouts", "value"),
)
def create_workout(
    add, row_deleted, saved_workout_selected, current, saved_workout_value
):
    """
    Callback controlling the editing of the create workout datatable

    Inputs:
        add (int): the number of clicks on the "add interval" button
        row_deleted (list): the data in the workout-editor table prior to a row deletion
        saved_workout_selected (int): the number of clicks on the "select workout" button.
            used to retrieve a saved workout from redis

    States:
        current (list): the workout data as it currently exists in the workout editor table
        saved_workout_value (str): the name of the selected saved workout

    Outputs:
        list: the workout data in the workout editor table
        str: the name of the workout
    """
    trigger = ctx.triggered_id  # callback context

    # Load workout from redis
    if trigger == "select-workout" and saved_workout_selected:
        return json.loads(
            redis_instance.hget("saved_workouts", saved_workout_value.encode("utf-8"))
        ), saved_workout_value.replace("_", " ")

    # Update interval numbers when row is deleted
    if trigger == "workout-editor" and len(current) < len(row_deleted):
        i = 1
        for row in current:
            row["interval"] = i
            i += 1

    # Add new row
    if trigger == "add-interval" and add:
        if current:
            next_interval = current[-1]["interval"] + 1
        else:
            next_interval = 1
        current.append(
            {
                "interval": next_interval,
                "exercise": "Exercise {}".format(next_interval),
                "duration": DEFAUlT_DURATION,
                "sub-intervals": 1,
            }
        )
    return current, no_update


@callback(
    Output("load-workout-modal", "is_open"),
    Output("saved-workouts", "options"),
    Output("load-workout-alert", "is_open"),
    Input("load-workout", "n_clicks"),
    Input("select-workout", "n_clicks"),
)
def load_saved_workouts(load_clicks, select_clicks):
    """
    Callback controlling the selection of saved workouts via the load-workout-modal

    Inputs:
        load_clicks (int): the number of times the "load workout" button has been clicked
        select_clicks (int): the number of timees the "select workout" button has been clicked

    Outputs:
        bool: whether or not the load-workout-modal is open
        list: the dropdown options for the saved-workouts dropdown
        bool: whether or not the load-workout-alert is displayed
    """
    trigger = ctx.triggered_id

    # Selecting a saved workout
    if trigger == "select-workout" and select_clicks:
        return False, no_update, no_update

    # Preventing select workout modal from opening on page load
    if not load_clicks:
        return no_update, no_update, no_update

    # Load saved workouts from redis - uses try/except to handle redis connection issues
    try:
        saved_workouts = [
            w.decode("utf-8") for w in redis_instance.hkeys("saved_workouts")
        ]  # Decode saved names to string format
    except:
        saved_workouts = []

    # Return empty list if there are no saved workouts, or no connection to redis
    if not len(saved_workouts):
        return False, no_update, True

    # Format workout names to be displayed
    saved_workouts = [
        {"label": w.replace("_", " "), "value": w} for w in saved_workouts
    ]
    return True, saved_workouts, no_update


@callback(
    Output("save-workout-alert", "children"),
    Output("save-workout-alert", "is_open"),
    Output("save-workout-alert", "color"),
    Input("save-workout", "n_clicks"),
    State("workout-name", "value"),
    State("workout-editor", "data"),
)
def save_workout(n_clicks, workout_name, data):
    """
    Callback controlling the 'save workout' functionality

    Inputs:
        n_clicks (int): the number of times the save-workout button has been clicked

    States:
        workout_name (str): the name of the workout to be saved
        data (list): the workout data as it exists in the workout editor table

    Outputs:
        str: the message to be displayed when a user attempts to save a workout
        bool: whether or not the save-workout-alert is displayed
        str: the color of the alert, according to the dbc options
    """
    if not n_clicks:
        return no_update, no_update, no_update

    # Prevent user from saving an empty workout
    if not len(data):
        return "Workout is empty!", True, "danger"

    # Create workout name if user deleted it
    if not workout_name:
        workout_name = "Workout #{}".format(random_workout_id)

    workout_id = workout_name.replace(
        " ", "_"
    )  # remove spaces from name to create workout_id
    try:
        # Display success message if data is successfully set in redis
        redis_instance.hset("saved_workouts", workout_id, json.dumps(data))
        return "'{}' successfully saved!".format(workout_name), True, "success"
    except:
        # Alert user if redis cannot be accessed
        return (
            "Cannot save workout because redis connection cannot be established",
            True,
            "danger",
        )


@callback(Output("select-workout", "disabled"), Input("saved-workouts", "value"))
def allow_saved_workout_selection(selection):
    """
    Callback controlling whether or not the "Select Workout" button can be pressed
    Inputs:
        selection (str): the name of the saved workout (according to redis)

    Outputs:
        bool: whether or not the select-workout button is disabled
    """

    return False if selection else True


@callback(
    Output("workout-plan", "data"),
    Output("workout-modal", "is_open"),
    Output("workout-launch-alert", "children"),
    Output("workout-launch-alert", "is_open"),
    Input("launch-workout", "n_clicks"),
    Input("close-workout", "n_clicks"),
    State("workout-editor", "data"),
)
def workout_mode(launch, close, table):
    """
    Callback which launches workout mode and stores data in workout-plan

    Inputs:
        launch (int): the number of clicks on the "launch workout" button
        close (int): the number of clicks on the "close workout" button

    States:
        table (list): the data in the workout editor table, with each list item corresponding
            to a row in the table

    Outputs:
        dict: the schema of the workout
        bool: whether the workout modal is open
        str: the content of workout-launch-alert, should there be an issue with launching
            the workout (e.g. workout is empty)
        bool: whether the workout-launch-alert should be displayed
    """
    trigger = ctx.triggered_id  # callback context

    # Reset workout data when workout is closed
    if trigger == "close-workout" and close:
        return [], False, no_update, no_update

    # Prevent opening of workout modal until launch button is pressed
    if not launch:
        return no_update, no_update, no_update, no_update

    # Handling the case where workout is empty
    if not len(table):
        return (no_update, no_update, "Please add at least 1 interval", True)

    # Converts tabular workout data to data to be stored in "workout-plan"
    plan = create_workout_plan(
        table, timestamp=START_COUNTDOWN
    )  # start first exercise after START_COUNTDOWN seconds

    # Display error if there are issues with the workout_plan
    if type(plan) == str:
        return no_update, no_update, plan, True

    return plan, True, no_update, no_update


@callback(
    Output("workout-timer", "disabled"),
    Output("workout-content", "children"),
    Output("pause-workout", "children"),
    Output("trigger-audio", "data"),
    Output("workout-timer", "n_intervals"),
    Output("pause-workout", "disabled"),
    Output("next-exercise", "children"),
    Input("start-workout", "n_clicks"),
    Input("pause-workout", "n_clicks"),
    Input("close-workout", "n_clicks"),
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
    State("workout-timer", "disabled"),
    prevent_initial_call=True,
)
def operate_workout(
    start_click, pause_click, close_workout, n_intervals, workout_plan, timer_disabled
):
    """
    Callback which operates while the workout is launched. Handles the start, pause, and close
    buttons, the timer, and the data displayed on the workout screen

    Inputs:
        start_click (int): the number of times the start-workout button has been clicked
        pause_workout (int): the number of times the pause-workout button has been clicked
        close_workout (int): the number of times the close-workout button has been clicked
        n_intervals (int): the number of seconds elapsed on the workout timer. this value
            does not accumulate when workout-timer is disabled

    States:
        workout-plan (dict): the schema of the workout. contains the timestamp markers and
            their corresponding exercises and audio sounds. also contains metadata such as
            the total workout duration
        timer_disabled (bool): indicates whether or not the workout-timer is currently disabled

    Outputs:
        bool: whether or not the workout-timer is disabled (e.g. when the pause or close button
            are pressed)
        str: the name of the exercise for the current interval
        str: the text displayed on the pause button (changes to 'resume' when the workout is
            currently paused)
        str: the name of the audio to be played - either "bell", "beep", or "short_beep"
        int: the number of seconds elapsed on the workout timer. this value is reset when the
            workout is closed
        bool: whether or not the pause-workout button is disabled
        str: the name of the exercise for the next interval
    """

    # Establish callback context - determines which input caused the callback to fire
    trigger = ctx.triggered_id

    # If start button pressed again while workout has already started, nothing happens
    if trigger == "start-workout" and not timer_disabled:
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    # Start the workout
    elif trigger == "start-workout" and start_click:
        first_exercise = (
            "Up next: "
            + workout_plan[str(workout_plan["timestamp_list"][0])]["exercise"]
        )
        return False, "Starting workout", no_update, "bell", 0, False, first_exercise

    # Close workout - reset n_intervals
    if trigger == "close-workout":
        return True, "Workout not started", "Pause workout", "bell", 0, True, ""

    # Pause workout
    if trigger == "pause-workout" and pause_click:
        if timer_disabled:
            return (
                False,
                no_update,
                "Pause Workout",
                no_update,
                no_update,
                no_update,
                no_update,
            )
        else:
            return (
                True,
                no_update,
                "Resume Workout",
                no_update,
                no_update,
                no_update,
                no_update,
            )

    # Update content based on timer
    # This section of code runs when n_intervals matches a timestamp in workout_plan
    if trigger == "workout-timer" and n_intervals in workout_plan["timestamp_list"]:
        timestamp_str = str(n_intervals)  # timestamp keys in workout_plan are strings
        current_exercise = workout_plan[timestamp_str]["exercise"]
        if current_exercise == "Finished":
            disabled = True
            next_exercise = ""
        else:
            disabled = no_update
            next_exercise = find_next_exercise(
                workout_plan, n_intervals, current_exercise
            )
        return (
            disabled,
            current_exercise,
            no_update,
            workout_plan[timestamp_str]["audio"],
            n_intervals,
            disabled,
            next_exercise,
        )

    # No updates when timer does not match a timestamp in workout_plan
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update


@callback(
    Output("audio-player", "src"),
    Input("trigger-audio", "data"),
)
def change_audio(audio):
    """
    Updates the audio sound based on the place in the workout (i.e. start and end with the
        'bell' sound, use a 'beep' when changing exercises, use 'short_beep' for sub-intervals)

    Inputs:
        audio (str): the name of the audio sound to be played

    Outputs:
        str: the url of the audio file corresponding to the desired sound
    """
    return "/assets/{}.mp3".format(audio)


@callback(
    Output("progress-bar", "value"),
    Output("progress-bar", "label"),
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
    prevent_intial_call=True,
)
def progress_bar(n_intervals, workout_plan):
    """
    Controls the progress bar at the bottom of the launched workout page

    Inputs:
        n_intervals (int): The number of seconds elapsed in the workout

    States:
        workout_plan (dict): The schema of the workout. Importantly, contains the total
            duration of the workout

    Outputs:
        int: The percent completion of the workout
        str: String representation of the percent completion
    """
    if not n_intervals:
        return 0, "0% complete"
    else:
        total_duration = workout_plan["total_duration"]
        progress = int((n_intervals / total_duration) * 100)
        return progress, "{}%".format(progress)


@callback(
    Output("countdown", "children"),
    Input("workout-timer", "n_intervals"),
    State("workout-plan", "data"),
    State("countdown", "children"),
    prevent_initial_call=True,
)
def count_down(n_intervals, workout_plan, current_count):
    """
    Callback which controls the interval countdown

    Inputs:
        n_intervals (int): the number of seconds elapsed in the workout

    States:
        workout-plan (dict): the schema of the workout. contains the timestamp markers and
            their corresponding exercises and audio sounds. also contains metadata such as
            the total workout duration
        current_count (int): the value currently displayed in the countdown

    Outputs:
        int: the value to be displayed in the countdown
    """

    # If workout has not started
    if int(n_intervals) == 0:
        return START_COUNTDOWN

    # When new interval begins, update the countdown
    if (
        n_intervals in workout_plan["timestamp_list"]
        and workout_plan[str(n_intervals)]["countdown"]  # countdown in non-zero
    ):
        return workout_plan[str(n_intervals)]["countdown"]

    # Stop counting when countdown reaches zero
    elif current_count == 0:
        return no_update

    # Decrease the countdown by 1 if no interval change
    else:
        return current_count - 1


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
"""
Clientside callback to make the audio sound

Inputs:
    trigger-audio (str): the name of the audio sound to be played

Outputs
    str: a dummy output, no purpose other than to have a complete callback
"""


if __name__ == "__main__":
    app.run(debug=True)

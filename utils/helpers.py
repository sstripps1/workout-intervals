import string
import random


def create_sub_interval_timestamps(duration, sub_intervals):
    """
    Creates the relative timestamps based on the interval duration and number of
        sub-intervals e.g. 60s duration with 3 sub-intervals would be [20, 40, 60]

    Inputs:
        duration (int): the interval duration, in seconds
        sub_intervals (int): the number of sub-intervals

    Outputs:
        list: contains the relative timestamps of the sub_intervals
    """
    sub_interval_duration = duration / sub_intervals
    timestamps = [round(sub_interval_duration * i) for i in range(1, sub_intervals + 1)]
    timestamps[-1] = duration  # account for uneven split
    return timestamps


def random_workout_id():
    """
    Creates random workout id for un-named workouts

    Outputs:
        str: random workout id
    """
    return "Workout #" + "".join(random.choice(string.digits) for i in range(4))


def create_workout_plan(table, timestamp):
    """
    Turns the tabular workout data into a dictionary readable during the workout

    Inputs:
        table (list): the tabular workout data
        timestamp (int): the starting timestamp

    Outputs:
        dict: contains the workout data
    """
    plan = {}
    for interval in table:
        duration = int(interval["duration"])
        exercise = interval["exercise"]
        sub_intervals = int(interval["sub-intervals"])
        if sub_intervals > duration:  # error catching
            return "Please ensure no sub-intervals exceed interval duration"
        if sub_intervals <= 1:  # ie no sub intervals
            plan[timestamp] = {
                "exercise": exercise,
                "audio": "beep",
                "countdown": duration,
            }
        else:  # ie there are sub-intervals
            sub_interval_timestamps = create_sub_interval_timestamps(
                duration, sub_intervals
            )
            sub_timestamp = 0
            interval_audio = "beep"
            countdown = duration
            for si in sub_interval_timestamps:
                plan[timestamp + sub_timestamp] = {
                    "exercise": exercise,
                    "audio": interval_audio,
                    "countdown": countdown,
                }
                sub_timestamp = si
                interval_audio = "short_beep"
                countdown = 0  # do not update countdown after first iteration
        timestamp += duration

    # Add in "Finished" to plan
    plan[timestamp] = {"exercise": "Finished", "audio": "bell", "countdown": 0}
    plan["timestamp_list"] = list(
        plan.keys()
    )  # additionally store timestamp keys in list
    plan["total_duration"] = timestamp

    return plan


def find_next_exercise(workout_plan, n_intervals, current_exercise):
    """
    Determines which exercise is "up next"

    Inputs:
        workout_plan (dict): the schema of the workout
        n_intervals (int): the number of seconds elapsed in the workout
        current_exercise (str): the name of the current exercise

    Outputs:
        str: the name of the next exercise
    """
    timestamp_list = workout_plan["timestamp_list"]
    i = 1
    while i < len(timestamp_list):
        next_exercise_timestamp = str(
            timestamp_list[timestamp_list.index(n_intervals) + i]
        )
        next_exercise = workout_plan[next_exercise_timestamp]["exercise"]
        if next_exercise != current_exercise:
            return "Up next: " + next_exercise
        else:
            i += 1
